from datetime import datetime, timedelta
from typing import Any
from jose import jwt, JWTError
from app.core.config import settings

# -------- 签发 --------
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=8) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# -------- 验签 --------
def verify_token(token: str) -> dict:
    """
    成功返回 payload（含 user_id 等）
    失败抛 JWTError，由调用者捕获统一处理 401
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise JWTError("Token 无效或已过期")