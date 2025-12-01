from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import verify_token
from app.models.user import User

# 从请求头 Authorization: Bearer <token> 里提取 token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme),
                     db: Session = Depends(get_db)) -> User:
    """
    验签成功 → 返回当前用户 ORM 对象
    失败 → 直接抛 401
    """
    try:
        payload = verify_token(token)
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token 无效",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user