from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet


def _get_fernet():
    return Fernet(settings.ENCRYPTION_KEY.encode())


class EncryptedTextField(models.TextField):
    def get_internal_type(self):
        return "TextField"

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except Exception:
            return value

    def to_python(self, value):
        if value is None:
            return value
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except Exception:
            return value

    def get_prep_value(self, value):
        if value is None:
            return None
        return _get_fernet().encrypt(value.encode()).decode()
