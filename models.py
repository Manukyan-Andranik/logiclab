import uuid
import datetime
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import secrets
import hmac
import hashlib
import base64

class ShortTokenManager:
    def __init__(self, secret_key="logic"):
        self.secret_key = secret_key.encode()

    def _sign(self, msg: bytes) -> str:
        sig = hmac.new(self.secret_key, msg, hashlib.sha1).digest()
        return base64.urlsafe_b64encode(sig)[:4].decode()  # Very short signature

    def generate_token(self, course_id: str) -> str:
        cid = course_id[:2]  # Assume course ID is small
        rand = secrets.token_hex(2)  # 4 chars
        token_body = f"{cid}{rand}".encode()
        sig = self._sign(token_body)
        return f"{cid}{rand}{sig}"  # Example: 'ml4ab2P1ZQ'

    def verify_token(self, token: str) -> bool:
        body = token[:-4].encode()
        expected_sig = self._sign(body)
        return token[-4:] == expected_sig


class User(UserMixin):
    pass

class TokenManager:
    def __init__(self):
        self.SECRET_KEY = "your_secret_key"
        self.SALT = "your_secret_salt"

    # Initialize serializer
    def _get_serializer(self):
        return URLSafeTimedSerializer(self.SECRET_KEY, salt=self.SALT)

    # In TokenManager class:
    def _generate_api_key(self, course_id: str, expiration_months: int=13) -> str:
        data = {
            'course_id': course_id,
            'uuid': str(uuid.uuid4()),
            'duration_months': expiration_months,
            'created_at': datetime.datetime.now().isoformat()
        }
        serializer = self._get_serializer()
        return serializer.dumps(data)

    def _decode_api_key(self, token: str, expiration_months: int) -> dict:
        serializer = self._get_serializer()
        max_age = expiration_months * 30 * 24 * 60 * 60
        try:
            data = serializer.loads(token, max_age=max_age)
            return {
                'valid': True,
                'data': data,
                'uuid': data.get('uuid'),
                'duration_months': data.get('duration_months'),
                'created_at': data.get('created_at')
            }
        except SignatureExpired:
            return {'valid': False, 'error': 'Token expired', 'expired': True}
        except BadSignature:
            return {'valid': False, 'error': 'Invalid token', 'expired': False}