from __future__ import annotations

from dataclasses import dataclass, field

from anthropic import Anthropic

from app.config import Settings


class ClaudeConfigurationError(RuntimeError):
    """Raised when Claude is requested without complete provider configuration."""


@dataclass(frozen=True)
class ClaudeClient:
    """Configured SDK client plus the bounded values used for every request."""

    sdk: Anthropic = field(repr=False)
    model: str
    timeout_seconds: float
    max_output_tokens: int
    max_retries: int
    temperature: float

    def close(self) -> None:
        """Release the SDK's underlying HTTP resources."""
        self.sdk.close()


def create_claude_client(settings: Settings) -> ClaudeClient:
    """Create a bounded synchronous client without making a provider request."""
    if settings.anthropic_api_key is None:
        raise ClaudeConfigurationError("ANTHROPIC_API_KEY is not configured.")

    sdk = Anthropic(
        api_key=settings.anthropic_api_key.get_secret_value(),
        timeout=settings.anthropic_timeout_seconds,
        max_retries=settings.anthropic_max_retries,
    )
    return ClaudeClient(
        sdk=sdk,
        model=settings.anthropic_model,
        timeout_seconds=settings.anthropic_timeout_seconds,
        max_output_tokens=settings.anthropic_max_output_tokens,
        max_retries=settings.anthropic_max_retries,
        temperature=settings.anthropic_temperature,
    )
