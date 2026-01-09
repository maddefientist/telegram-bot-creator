"""Moderation module - message filtering."""
import re
from collections import defaultdict

import structlog

from spec import BotSpec

logger = structlog.get_logger()


class ModerationModule:
    """Handles message moderation and filtering."""

    def __init__(self, spec: BotSpec):
        self.spec = spec
        self.config = spec.moderation

        # Compile blocked words regex
        if self.config.blocked_words:
            pattern = "|".join(
                re.escape(word) for word in self.config.blocked_words
            )
            self.blocked_pattern = re.compile(pattern, re.IGNORECASE)
        else:
            self.blocked_pattern = None

        # URL regex
        self.url_pattern = re.compile(
            r"https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}(?:/[^\s]*)?",
            re.IGNORECASE,
        )

        # Warning counts
        self.warnings: dict[int, int] = defaultdict(int)

    async def check_message(
        self,
        text: str,
        user_id: int,
        chat_id: int,
    ) -> tuple[bool, str]:
        """
        Check if message should be blocked.

        Returns:
            tuple: (should_block, reason)
        """
        # Check blocked words
        if self.blocked_pattern and self.blocked_pattern.search(text):
            self._record_violation(user_id)
            return True, "Blocked word detected"

        # Check links
        if self.config.block_links and self.url_pattern.search(text):
            self._record_violation(user_id)
            return True, "Links not allowed"

        return False, ""

    def _record_violation(self, user_id: int) -> None:
        """Record a violation for a user."""
        self.warnings[user_id] += 1

        logger.info(
            "Moderation violation",
            user_id=user_id,
            warnings=self.warnings[user_id],
        )

    def get_warning_count(self, user_id: int) -> int:
        """Get warning count for a user."""
        return self.warnings[user_id]

    def should_ban(self, user_id: int) -> bool:
        """Check if user should be banned based on warnings."""
        return self.warnings[user_id] >= self.config.warn_before_ban

    def reset_warnings(self, user_id: int) -> None:
        """Reset warnings for a user."""
        self.warnings[user_id] = 0
