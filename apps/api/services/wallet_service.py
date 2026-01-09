"""Solana wallet signature verification service."""
import secrets
from datetime import datetime, timedelta, timezone

import base58
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from solders.pubkey import Pubkey
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from models.wallet_nonce import WalletNonce

logger = get_logger(__name__)


class WalletService:
    """Service for Solana wallet authentication."""

    NONCE_EXPIRY_MINUTES = 5
    MESSAGE_PREFIX = "Sign this message to authenticate with Telegram Bot Creator.\n\nNonce: "

    async def generate_nonce(
        self,
        db: AsyncSession,
        wallet_address: str,
    ) -> tuple[str, str]:
        """
        Generate a one-time nonce for signature challenge.

        Args:
            db: Database session
            wallet_address: Solana public key (base58)

        Returns:
            tuple: (nonce, full_message_to_sign)

        Raises:
            ValueError: If wallet address is invalid
        """
        # Validate wallet address format
        try:
            Pubkey.from_string(wallet_address)
        except Exception as e:
            logger.warning("Invalid wallet address", wallet_address=wallet_address, error=str(e))
            raise ValueError("Invalid Solana wallet address")

        # Generate cryptographically secure nonce
        nonce = secrets.token_urlsafe(32)

        # Create message to sign
        message = f"{self.MESSAGE_PREFIX}{nonce}"

        # Store nonce in database
        wallet_nonce = WalletNonce(
            wallet_address=wallet_address,
            nonce=nonce,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=self.NONCE_EXPIRY_MINUTES),
        )
        db.add(wallet_nonce)
        await db.commit()

        logger.info(
            "Generated nonce for wallet",
            wallet_address=wallet_address[:8] + "...",
            expires_in_minutes=self.NONCE_EXPIRY_MINUTES,
        )

        return nonce, message

    async def verify_signature(
        self,
        db: AsyncSession,
        wallet_address: str,
        signature: str,
        nonce: str,
    ) -> bool:
        """
        Verify a wallet signature against stored nonce.

        Args:
            db: Database session
            wallet_address: Solana public key (base58)
            signature: Signed message signature (base58)
            nonce: The nonce that was signed

        Returns:
            bool: True if signature is valid and nonce is unused
        """
        # Validate wallet address
        try:
            pubkey = Pubkey.from_string(wallet_address)
        except Exception as e:
            logger.warning("Invalid wallet address during verification", wallet_address=wallet_address, error=str(e))
            return False

        # Find and validate nonce
        result = await db.execute(
            select(WalletNonce).where(
                WalletNonce.wallet_address == wallet_address,
                WalletNonce.nonce == nonce,
                WalletNonce.used == False,  # noqa: E712
                WalletNonce.expires_at > datetime.now(timezone.utc),
            )
        )
        nonce_record = result.scalar_one_or_none()

        if not nonce_record:
            logger.warning(
                "Nonce not found or expired",
                wallet_address=wallet_address[:8] + "...",
            )
            return False

        # Reconstruct the message that was signed
        message = f"{self.MESSAGE_PREFIX}{nonce}"
        message_bytes = message.encode("utf-8")

        try:
            # Decode signature from base58
            signature_bytes = base58.b58decode(signature)

            # Get public key bytes
            pubkey_bytes = bytes(pubkey)

            # Verify signature using Ed25519
            verify_key = VerifyKey(pubkey_bytes)
            verify_key.verify(message_bytes, signature_bytes)

            # Mark nonce as used
            nonce_record.used = True
            await db.commit()

            logger.info(
                "Signature verified successfully",
                wallet_address=wallet_address[:8] + "...",
            )

            return True

        except (BadSignatureError, ValueError, Exception) as e:
            logger.warning(
                "Signature verification failed",
                wallet_address=wallet_address[:8] + "...",
                error=str(e),
            )
            return False

    async def cleanup_expired_nonces(self, db: AsyncSession) -> int:
        """
        Remove expired nonces from database.

        Args:
            db: Database session

        Returns:
            int: Number of deleted records
        """
        result = await db.execute(
            delete(WalletNonce).where(
                WalletNonce.expires_at < datetime.now(timezone.utc)
            )
        )
        await db.commit()

        count = result.rowcount or 0
        if count > 0:
            logger.info("Cleaned up expired nonces", count=count)

        return count
