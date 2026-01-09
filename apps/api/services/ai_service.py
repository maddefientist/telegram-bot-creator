"""AI service for generating BotSpec via OpenRouter."""
import json
import re
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings
from core.logging import get_logger
from schemas.botspec import BotSpec, BOTSPEC_JSON_SCHEMA, ModuleType

settings = get_settings()
logger = get_logger(__name__)


# System prompt for BotSpec generation
SYSTEM_PROMPT = """You are a Telegram bot configuration generator. Your ONLY task is to output valid JSON that conforms to the BotSpec schema.

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown, no code blocks, no explanation
2. The JSON must conform exactly to the BotSpec schema
3. Never include executable code, file operations, or system commands
4. Never generate content that could be harmful, illegal, or unethical
5. Keep responses focused on legitimate bot functionality

BotSpec JSON Schema:
{schema}

Available modules:
- basic_commands: Provides /start and /help commands
- static_replies: Predefined command responses
- ai_chat: AI-powered conversational responses (uses OpenRouter)
- moderation: Message filtering and user management
- webhook_forward: Forward events to external HTTPS URLs

Command response_type options: "text", "markdown", "html"

IMPORTANT CONSTRAINTS:
- command names: lowercase letters, numbers, underscores only (no spaces)
- system_prompt: NO instructions to ignore rules, execute code, or access files
- webhook.url: MUST be HTTPS, CANNOT be localhost or private IPs
- All string fields have length limits - be concise

Output the BotSpec JSON and nothing else."""

REPAIR_PROMPT = """The previous JSON output was invalid. Fix the following errors and output ONLY the corrected JSON:

Errors:
{errors}

Previous output:
{previous}

Output ONLY the corrected JSON, no explanation."""


class AIService:
    """Service for AI-powered BotSpec generation."""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
        self.model = settings.openrouter_model

    async def generate_botspec(
        self,
        description: str,
        bot_name: str,
        enabled_modules: list[ModuleType],
        constraints: str = "",
    ) -> tuple[dict[str, Any] | None, list[str], int, int]:
        """
        Generate a BotSpec from natural language description.

        Returns:
            tuple: (spec_dict, errors, tokens_used, retries)
        """
        total_tokens = 0
        retries = 0

        # Build the user prompt
        user_prompt = self._build_user_prompt(
            description, bot_name, enabled_modules, constraints
        )

        # First attempt
        spec_json, tokens, errors = await self._generate_and_validate(user_prompt)
        total_tokens += tokens

        # Retry with repair prompt if needed (up to 2 retries)
        while errors and retries < 2:
            retries += 1
            logger.info(
                "Retrying BotSpec generation",
                retry=retries,
                errors=errors,
            )

            repair_user_prompt = REPAIR_PROMPT.format(
                errors="\n".join(errors),
                previous=json.dumps(spec_json) if spec_json else "Invalid JSON",
            )

            spec_json, tokens, errors = await self._generate_and_validate(
                repair_user_prompt
            )
            total_tokens += tokens

        if errors:
            logger.warning(
                "BotSpec generation failed after retries",
                errors=errors,
            )
            return None, errors, total_tokens, retries

        return spec_json, [], total_tokens, retries

    def _build_user_prompt(
        self,
        description: str,
        bot_name: str,
        enabled_modules: list[ModuleType],
        constraints: str,
    ) -> str:
        """Build the user prompt for generation."""
        module_list = ", ".join(m.value for m in enabled_modules)

        prompt = f"""Create a BotSpec for a Telegram bot with:

Name: {bot_name}
Description: {description}
Enabled modules: {module_list}
"""
        if constraints:
            prompt += f"\nAdditional requirements: {constraints}"

        prompt += "\n\nOutput the BotSpec JSON:"
        return prompt

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def _call_openrouter(self, user_prompt: str) -> tuple[str, int]:
        """Call OpenRouter API with retry logic."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.format(
                        schema=json.dumps(BOTSPEC_JSON_SCHEMA, indent=2)
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,  # Lower temperature for more consistent JSON
            max_tokens=2000,
            response_format={"type": "json_object"},  # Request JSON mode if supported
        )

        content = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0

        return content, tokens

    async def _generate_and_validate(
        self, user_prompt: str
    ) -> tuple[dict[str, Any] | None, int, list[str]]:
        """Generate and validate a single attempt."""
        errors: list[str] = []

        try:
            content, tokens = await self._call_openrouter(user_prompt)
        except Exception as e:
            logger.error("OpenRouter API error", error=str(e))
            return None, 0, [f"API error: {str(e)}"]

        # Extract JSON from response (handle markdown code blocks)
        json_str = self._extract_json(content)
        if not json_str:
            return None, tokens, ["No valid JSON found in response"]

        # Parse JSON
        try:
            spec_dict = json.loads(json_str)
        except json.JSONDecodeError as e:
            return None, tokens, [f"JSON parse error: {str(e)}"]

        # Validate against BotSpec schema
        try:
            validated = BotSpec.model_validate(spec_dict)
            return validated.model_dump(), tokens, []
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                loc = ".".join(str(l) for l in error["loc"])
                error_messages.append(f"{loc}: {error['msg']}")
            return spec_dict, tokens, error_messages

    def _extract_json(self, content: str) -> str | None:
        """Extract JSON from response, handling markdown code blocks."""
        content = content.strip()

        # If already valid JSON
        if content.startswith("{"):
            return content

        # Try to extract from markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            return json_match.group(1).strip()

        # Try to find JSON object
        brace_match = re.search(r"\{[\s\S]*\}", content)
        if brace_match:
            return brace_match.group(0)

        return None

    def validate_spec(self, spec_dict: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a BotSpec dictionary."""
        try:
            BotSpec.model_validate(spec_dict)
            return True, []
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                loc = ".".join(str(l) for l in error["loc"])
                error_messages.append(f"{loc}: {error['msg']}")
            return False, error_messages
