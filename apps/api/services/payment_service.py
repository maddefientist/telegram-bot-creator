"""Solana payment verification service."""
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import base58
import httpx
from solders.pubkey import Pubkey
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings
from core.logging import get_logger
from core.security import generate_reference_key

settings = get_settings()
logger = get_logger(__name__)

# SOL has 9 decimal places
LAMPORTS_PER_SOL = 1_000_000_000


class PaymentService:
    """Service for Solana payment verification using reference keys."""

    def __init__(self):
        self.rpc_url = settings.solana_rpc_url
        self.treasury_address = settings.solana_treasury_address

    def create_invoice_data(
        self,
        amount_sol: float,
        bot_name: str,
    ) -> dict[str, Any]:
        """
        Create invoice data with unique reference for Solana Pay.

        Uses Solana Pay reference key method - a unique public key is
        generated for each invoice. The payment transaction must include
        this reference as an account in the instruction.
        """
        # Generate unique reference key (like a public key)
        reference = generate_reference_key()

        # Create Solana Pay URL
        # Format: solana:<recipient>?amount=<amount>&reference=<ref>&label=<label>&message=<msg>
        params = {
            "amount": str(amount_sol),
            "reference": reference,
            "label": "Bot Subscription",
            "message": f"Payment for {bot_name}",
        }

        solana_pay_url = f"solana:{self.treasury_address}?{urlencode(params)}"

        # Expiry time
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.invoice_expiry_hours
        )

        return {
            "amount_sol": amount_sol,
            "treasury_address": self.treasury_address,
            "reference": reference,
            "solana_pay_url": solana_pay_url,
            "expires_at": expires_at,
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def _rpc_request(self, method: str, params: list[Any]) -> dict[str, Any]:
        """Make an RPC request to Solana."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params,
                },
            )
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                raise Exception(f"RPC error: {data['error']}")

            return data.get("result", {})

    async def verify_payment(
        self,
        reference: str,
        expected_amount_sol: float,
    ) -> tuple[bool, str | None, str]:
        """
        Verify a payment by searching for transactions with the reference key.

        Returns:
            tuple: (is_paid, tx_signature, message)
        """
        try:
            # Convert reference to Pubkey
            try:
                reference_pubkey = Pubkey.from_string(reference)
            except Exception as e:
                logger.error("Invalid reference key", reference=reference, error=str(e))
                return False, None, "Invalid reference key"

            # Get signatures for the reference address
            # This finds transactions that included this reference
            result = await self._rpc_request(
                "getSignaturesForAddress",
                [
                    str(reference_pubkey),
                    {"limit": 10},
                ],
            )

            if not result:
                return False, None, "No transactions found"

            # Check each transaction
            for sig_info in result:
                signature = sig_info.get("signature")
                if not signature:
                    continue

                # Get full transaction details
                tx_result = await self._rpc_request(
                    "getTransaction",
                    [
                        signature,
                        {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0},
                    ],
                )

                if not tx_result:
                    continue

                # Verify the payment
                is_valid, amount = self._verify_transaction(
                    tx_result,
                    expected_amount_sol,
                )

                if is_valid:
                    logger.info(
                        "Payment verified",
                        reference=reference,
                        signature=signature,
                        amount=amount,
                    )
                    return True, signature, f"Payment confirmed: {amount} SOL"

            return False, None, "No matching payment found"

        except Exception as e:
            logger.error(
                "Payment verification error",
                reference=reference,
                error=str(e),
            )
            return False, None, f"Verification error: {str(e)}"

    def _verify_transaction(
        self,
        tx_data: dict[str, Any],
        expected_amount_sol: float,
    ) -> tuple[bool, float]:
        """
        Verify a transaction meets payment requirements.

        Checks:
        1. Transaction was successful (no error)
        2. Recipient is treasury address
        3. Amount is >= expected
        """
        try:
            meta = tx_data.get("meta", {})

            # Check for errors
            if meta.get("err") is not None:
                return False, 0

            # Get pre and post balances to calculate transfer amount
            pre_balances = meta.get("preBalances", [])
            post_balances = meta.get("postBalances", [])

            transaction = tx_data.get("transaction", {})
            message = transaction.get("message", {})
            account_keys = message.get("accountKeys", [])

            # Find treasury account index
            treasury_index = None
            for i, account in enumerate(account_keys):
                pubkey = account.get("pubkey") if isinstance(account, dict) else account
                if pubkey == self.treasury_address:
                    treasury_index = i
                    break

            if treasury_index is None:
                return False, 0

            # Calculate amount received by treasury
            if treasury_index >= len(pre_balances) or treasury_index >= len(post_balances):
                return False, 0

            pre_balance = pre_balances[treasury_index]
            post_balance = post_balances[treasury_index]

            # Amount in lamports
            amount_lamports = post_balance - pre_balance
            amount_sol = amount_lamports / LAMPORTS_PER_SOL

            # Check if amount is sufficient (allow small tolerance for fees)
            min_amount = expected_amount_sol * 0.99  # 1% tolerance

            if amount_sol >= min_amount:
                return True, amount_sol

            return False, amount_sol

        except Exception as e:
            logger.error("Transaction verification error", error=str(e))
            return False, 0

    async def get_transaction_status(self, signature: str) -> dict[str, Any]:
        """Get the status of a transaction."""
        try:
            result = await self._rpc_request(
                "getTransaction",
                [
                    signature,
                    {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0},
                ],
            )

            if not result:
                return {"status": "not_found"}

            meta = result.get("meta", {})
            if meta.get("err"):
                return {"status": "failed", "error": meta["err"]}

            return {
                "status": "confirmed",
                "slot": result.get("slot"),
                "block_time": result.get("blockTime"),
            }

        except Exception as e:
            logger.error("Transaction status error", signature=signature, error=str(e))
            return {"status": "error", "error": str(e)}

    async def poll_for_payment(
        self,
        reference: str,
        expected_amount_sol: float,
        timeout_seconds: int = 300,
        poll_interval: int = 5,
    ) -> tuple[bool, str | None, str]:
        """
        Poll for payment until found or timeout.

        This is used by background workers to check for payments.
        """
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(seconds=timeout_seconds)

        while datetime.now(timezone.utc) < end_time:
            is_paid, signature, message = await self.verify_payment(
                reference, expected_amount_sol
            )

            if is_paid:
                return True, signature, message

            await asyncio.sleep(poll_interval)

        return False, None, "Payment verification timed out"
