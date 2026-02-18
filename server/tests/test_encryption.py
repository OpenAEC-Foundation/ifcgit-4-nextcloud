"""
Unit tests for the Fernet encrypt / decrypt helpers in ``src.auth.erpnext``.
"""

import pytest

from src.auth.erpnext import encrypt_secret, decrypt_secret


SECRET_KEY = "test-secret-key-for-unit-tests"
WRONG_KEY = "completely-different-key"


class TestEncryptDecryptRoundTrip:
    """encrypt_secret -> decrypt_secret should return the original value."""

    def test_roundtrip_basic(self):
        plaintext = "my-api-secret-12345"
        cipher = encrypt_secret(plaintext, SECRET_KEY)
        assert decrypt_secret(cipher, SECRET_KEY) == plaintext

    def test_roundtrip_unicode(self):
        plaintext = "geheim-wachtwoord-\u00e9\u00e8\u00ea"
        cipher = encrypt_secret(plaintext, SECRET_KEY)
        assert decrypt_secret(cipher, SECRET_KEY) == plaintext

    def test_roundtrip_long_string(self):
        plaintext = "x" * 10_000
        cipher = encrypt_secret(plaintext, SECRET_KEY)
        assert decrypt_secret(cipher, SECRET_KEY) == plaintext


class TestDecryptWithWrongKey:
    """Decrypting with a different key must return an empty string (not raise)."""

    def test_wrong_key_returns_empty(self):
        cipher = encrypt_secret("secret", SECRET_KEY)
        result = decrypt_secret(cipher, WRONG_KEY)
        assert result == ""

    def test_garbage_ciphertext_returns_empty(self):
        result = decrypt_secret("not-a-valid-fernet-token", SECRET_KEY)
        assert result == ""


class TestCiphertextUniqueness:
    """
    Fernet tokens include a timestamp and random IV, so encrypting the
    same plaintext twice must produce different ciphertext.
    """

    def test_different_ciphertext_each_call(self):
        plaintext = "same-value"
        c1 = encrypt_secret(plaintext, SECRET_KEY)
        c2 = encrypt_secret(plaintext, SECRET_KEY)
        assert c1 != c2
        # Both must still decrypt to the original value.
        assert decrypt_secret(c1, SECRET_KEY) == plaintext
        assert decrypt_secret(c2, SECRET_KEY) == plaintext


class TestEmptyStringHandling:
    """Edge-case: encrypting / decrypting an empty string."""

    def test_encrypt_empty_string(self):
        cipher = encrypt_secret("", SECRET_KEY)
        assert isinstance(cipher, str)
        assert len(cipher) > 0  # Fernet always produces output

    def test_roundtrip_empty_string(self):
        cipher = encrypt_secret("", SECRET_KEY)
        assert decrypt_secret(cipher, SECRET_KEY) == ""
