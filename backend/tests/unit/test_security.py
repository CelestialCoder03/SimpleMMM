"""Tests for security utilities."""

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


def test_password_hash():
    """Test password hashing."""
    password = "testpassword123"
    hashed = get_password_hash(password)

    assert hashed != password
    assert hashed.startswith("$2b$")  # bcrypt prefix


def test_password_verify():
    """Test password verification."""
    password = "testpassword123"
    hashed = get_password_hash(password)

    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_create_access_token():
    """Test access token creation."""
    token = create_access_token(subject="test-user-id")

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_refresh_token():
    """Test refresh token creation."""
    token = create_refresh_token(subject="test-user-id")

    assert token is not None
    assert isinstance(token, str)


def test_decode_valid_token():
    """Test decoding a valid token."""
    subject = "test-user-id"
    token = create_access_token(subject=subject)

    payload = decode_token(token)

    assert payload is not None
    assert payload["sub"] == subject
    assert payload["type"] == "access"


def test_decode_invalid_token():
    """Test decoding an invalid token."""
    payload = decode_token("invalid-token")

    assert payload is None


def test_access_token_type():
    """Test access token has correct type."""
    token = create_access_token(subject="test")
    payload = decode_token(token)

    assert payload["type"] == "access"


def test_refresh_token_type():
    """Test refresh token has correct type."""
    token = create_refresh_token(subject="test")
    payload = decode_token(token)

    assert payload["type"] == "refresh"
