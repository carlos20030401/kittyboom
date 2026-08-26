from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
def hash_password(value: str): return pwd.hash(value)
def verify_password(value: str, hashed: str): return pwd.verify(value, hashed)
def create_token(user_id: int, role: str):
    return jwt.encode({"sub": str(user_id), "role": role, "exp": datetime.now(timezone.utc)+timedelta(hours=8)}, settings.jwt_secret, algorithm="HS256")
def decode_token(token: str):
    try: return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError: return None

