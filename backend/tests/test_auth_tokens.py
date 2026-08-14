import pytest

from app.auth.tokens import InvalidTokenError, generate_token, hash_token


def test_generated_token_is_canonical_and_hashable() -> None:
    token = generate_token()

    assert len(token) == 43
    assert len(hash_token(token)) == 32


@pytest.mark.parametrize(
    "token",
    ["", "short", "x" * 42, "x" * 44, "!" * 43, "é" * 43],
)
def test_hash_token_rejects_malformed_values(token: str) -> None:
    with pytest.raises(InvalidTokenError):
        hash_token(token)
