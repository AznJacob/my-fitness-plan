from unittest.mock import Mock, patch

import pytest

from app.claude.client import ClaudeConfigurationError, create_claude_client
from app.config import Settings

DATABASE_URL = "postgresql+psycopg://app_user:secret@postgres:5432/myfitnessplan"


def test_client_requires_api_key_only_when_provider_is_requested() -> None:
    settings = Settings.model_validate({"database_url": DATABASE_URL})

    with pytest.raises(ClaudeConfigurationError, match="ANTHROPIC_API_KEY"):
        create_claude_client(settings)


def test_client_uses_explicit_bounded_sdk_configuration() -> None:
    settings = Settings.model_validate(
        {
            "database_url": DATABASE_URL,
            "anthropic_api_key": "test-anthropic-key",
            "anthropic_model": "claude-haiku-test-snapshot",
            "anthropic_timeout_seconds": 45,
            "anthropic_max_output_tokens": 4_096,
            "anthropic_max_retries": 0,
            "anthropic_temperature": 0.1,
        }
    )
    sdk = Mock()

    with patch("app.claude.client.Anthropic", return_value=sdk) as sdk_constructor:
        client = create_claude_client(settings)

    sdk_constructor.assert_called_once_with(
        api_key="test-anthropic-key",
        timeout=45,
        max_retries=0,
    )
    assert client.model == "claude-haiku-test-snapshot"
    assert client.timeout_seconds == 45
    assert client.max_output_tokens == 4_096
    assert client.max_retries == 0
    assert client.temperature == 0.1
    assert "test-anthropic-key" not in repr(client)

    client.close()
    sdk.close.assert_called_once_with()
