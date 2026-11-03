from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", "30"))
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRY_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None

# For API endpoints using JWT Bearer token
def get_current_user_from_token(authorization: str = None):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        return None
    return payload

# For template pages using session cookie
def get_current_user_from_cookie(request, db):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    with db() as cur:
        cur.execute("""
            SELECT customer_id, name, email, phone, role, created_at 
            FROM Customer WHERE customer_id = %s
        """, (user_id,))
        row = cur.fetchone()
        if row:
            return {
                "customer_id": row[0],
                "name": row[1],
                "email": row[2],
                "phone": row[3],
                "role": row[4],
                "created_at": row[5]
            }
    return None
