import uuid
import datetime
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

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