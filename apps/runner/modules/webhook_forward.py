"""Webhook forward module - forwards events to external URL."""
import hashlib
import hmac
import json
from typing import Any

import httpx
import structlog

from spec import BotSpec

logger = structlog.get_logger()


class WebhookForwardModule:
    """Handles forwarding events to external webhook URLs."""

    def __init__(self, spec: BotSpec):
        self.spec = spec
        self.config = spec.webhook

    def _generate_signature(self, payload: bytes) -> str:
        """Generate HMAC signature for payload."""
        if not self.config.secret:
            return ""

        signature = hmac.new(
            self.config.secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return f"sha256={signature}"

    async def forward_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> bool:
        """Forward an event to the webhook URL."""
        if not self.config.enabled or not self.config.url:
            return False

        if event_type not in self.config.events:
            return False

        payload = {
            "event": event_type,
            "data": data,
        }

        payload_bytes = json.dumps(payload).encode()
        signature = self._generate_signature(payload_bytes)

        headers = {
            "Content-Type": "application/json",
            "X-Event-Type": event_type,
        }

        if signature:
            headers["X-Webhook-Signature"] = signature

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.url,
                    content=payload_bytes,
                    headers=headers,
                    timeout=10.0,
                )

                if response.status_code >= 400:
                    logger.warning(
                        "Webhook request failed",
                        url=self.config.url,
                        status=response.status_code,
                    )
                    return False

                return True

        except Exception as e:
            logger.error(
                "Webhook error",
                url=self.config.url,
                error=str(e),
            )
            return False
