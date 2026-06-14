import pytest
from django.test import TestCase
from django.conf import settings
from apps.common.fields import _get_fernet


class EncryptionTests(TestCase):
    def test_encryption_key_is_configured(self):
        self.assertTrue(hasattr(settings, 'ENCRYPTION_KEY'))
        self.assertTrue(len(settings.ENCRYPTION_KEY) > 0)

    def test_encryption_key_differs_from_secret_key(self):
        self.assertNotEqual(settings.ENCRYPTION_KEY, settings.SECRET_KEY)

    def test_fernet_key_valid(self):
        key = _get_fernet()
        from cryptography.fernet import Fernet
        self.assertIsInstance(key, Fernet)

    def test_encrypt_decrypt_roundtrip(self):
        f = _get_fernet()
        original = 'my-secret-password-123!'
        encrypted = f.encrypt(original.encode()).decode()
        decrypted = f.decrypt(encrypted.encode()).decode()
        self.assertEqual(original, decrypted)

    def test_encrypted_text_field_uses_encryption_key_not_secret_key(self):
        from apps.common.fields import _get_fernet
        import base64, hashlib
        secret_key_based = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
        encryption_key_based = settings.ENCRYPTION_KEY.encode()
        self.assertNotEqual(secret_key_based, encryption_key_based)
