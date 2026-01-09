"""AI Chat module - OpenRouter powered responses."""
import time
from collections import defaultdict
from typing import Any

from cachetools import TTLCache
from openai import AsyncOpenAI
from telegram.ext import ContextTypes
import structlog

from spec import BotSpec

logger = structlog.get_logger()


class AIChatModule:
    """Handles AI-powered chat responses."""

    def __init__(
        self,
        spec: BotSpec,
        api_key: str,
        model: str,
    ):
        self.spec = spec
        self.config = spec.ai_chat
        self.model = model

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        # Rate limiting
        self.user_requests: dict[int, list[float]] = defaultdict(list)
        self.daily_counts: dict[int, int] = defaultdict(int)
        self.daily_reset: float = time.time()

        # Conversation history cache (TTL: 1 hour)
        self.conversation_cache: TTLCache = TTLCache(maxsize=1000, ttl=3600)

    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limits."""
        now = time.time()

        # Reset daily counts if needed
        if now - self.daily_reset > 86400:  # 24 hours
            self.daily_counts.clear()
            self.daily_reset = now

        # Check daily limit
        if self.daily_counts[user_id] >= self.config.max_tokens:
            return False

        # Check per-minute limit
        minute_ago = now - 60
        recent = [t for t in self.user_requests[user_id] if t > minute_ago]
        self.user_requests[user_id] = recent

        if len(recent) >= self.spec.limits.max_messages_per_user_per_minute:
            return False

        return True

    def _record_request(self, user_id: int) -> None:
        """Record a request for rate limiting."""
        self.user_requests[user_id].append(time.time())
        self.daily_counts[user_id] += 1

    def _get_conversation_key(self, user_id: int, chat_id: int) -> str:
        """Get conversation cache key."""
        return f"{chat_id}:{user_id}"

    def _get_conversation(self, user_id: int, chat_id: int) -> list[dict[str, str]]:
        """Get conversation history."""
        key = self._get_conversation_key(user_id, chat_id)
        return self.conversation_cache.get(key, [])

    def _add_to_conversation(
        self,
        user_id: int,
        chat_id: int,
        role: str,
        content: str,
    ) -> None:
        """Add message to conversation history."""
        key = self._get_conversation_key(user_id, chat_id)
        history = self.conversation_cache.get(key, [])
        history.append({"role": role, "content": content})

        # Trim to max context
        if len(history) > self.config.max_context_messages * 2:
            history = history[-(self.config.max_context_messages * 2):]

        self.conversation_cache[key] = history

    def _check_content_safety(self, message: str) -> tuple[bool, str]:
        """Check if message content is safe to process."""
        message_lower = message.lower()

        # Check disallowed topics
        for topic in self.config.disallowed_topics:
            if topic.lower() in message_lower:
                return False, f"Topic not allowed: {topic}"

        # Check for prompt injection attempts
        dangerous_patterns = [
            "ignore previous",
            "ignore all",
            "disregard",
            "forget everything",
            "new instructions",
            "system prompt",
            "you are now",
            "act as",
            "pretend to be",
        ]

        for pattern in dangerous_patterns:
            if pattern in message_lower:
                return False, "Message contains restricted content"

        return True, ""

    async def generate_response(
        self,
        message: str,
        user_id: int,
        chat_id: int,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> str | None:
        """Generate AI response to user message."""
        # Rate limit check
        if not self._check_rate_limit(user_id):
            return "You've reached the message limit. Please try again later."

        # Content safety check
        is_safe, reason = self._check_content_safety(message)
        if not is_safe:
            logger.warning(
                "Blocked unsafe content",
                user_id=user_id,
                reason=reason,
            )
            return None  # Silently ignore

        # Record request
        self._record_request(user_id)

        # Build messages
        messages = [
            {"role": "system", "content": self.config.system_prompt},
        ]

        # Add conversation history
        history = self._get_conversation(user_id, chat_id)
        messages.extend(history)

        # Add current message
        messages.append({"role": "user", "content": message})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            assistant_message = response.choices[0].message.content or ""

            # Save to history
            self._add_to_conversation(user_id, chat_id, "user", message)
            self._add_to_conversation(user_id, chat_id, "assistant", assistant_message)

            return assistant_message

        except Exception as e:
            logger.error("AI generation error", error=str(e))
            return "Sorry, I couldn't generate a response. Please try again."
