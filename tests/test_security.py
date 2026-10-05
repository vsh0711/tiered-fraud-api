from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)
from app.config import Settings


def test_password_hash_roundtrip():
    h = hash_password("admin123")
    assert verify_password("admin123", h)
    assert not verify_password("wrong", h)


def test_api_key_hash_stable():
    raw = generate_api_key()
    assert hash_api_key(raw) == hash_api_key(raw)
    assert hash_api_key(raw) != hash_api_key(generate_api_key())


def test_jwt_roundtrip():
    settings = Settings(jwt_secret="unit-test-secret")
    token = create_access_token("admin", settings, expires_minutes=5)
    assert decode_access_token(token, settings) == "admin"
    assert decode_access_token("bad.token", settings) is None
