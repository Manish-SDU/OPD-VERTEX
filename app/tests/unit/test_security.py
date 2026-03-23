"""Unit tests for security utilities."""

from __future__ import annotations

from jose import jwt

from app.core.security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_session_payload,
    hash_password,
    verify_password,
)


class TestHashPassword:
    def test_returns_bcrypt_hash(self):
        hashed = hash_password("mypassword")
        assert hashed != "mypassword"
        assert hashed.startswith("$2")

    def test_different_calls_produce_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # different salts


class TestVerifyPassword:
    def test_correct_password(self):
        hashed = hash_password("secret123")
        assert verify_password("secret123", hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("secret123")
        assert verify_password("wrong", hashed) is False

    def test_empty_hash_returns_false(self):
        assert verify_password("anything", "") is False

    def test_invalid_hash_returns_false(self):
        assert verify_password("anything", "not-a-bcrypt-hash") is False


class TestCreateAccessToken:
    def test_returns_decodable_jwt(self):
        token = create_access_token({"sub": "user@example.com", "role": "doctor"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user@example.com"
        assert payload["role"] == "doctor"

    def test_token_contains_expiry(self):
        token = create_access_token({"sub": "user@example.com"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_does_not_mutate_input(self):
        data = {"sub": "test"}
        create_access_token(data)
        assert "exp" not in data


class TestCreateSessionPayload:
    def test_returns_expected_keys(self):
        payload = create_session_payload("user_1", "admin")
        assert payload == {"user_id": "user_1", "role": "admin"}
