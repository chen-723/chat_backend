from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin
from app.core.security import create_access_token

# ---- 注册 ----
def register_user(db: Session, req: UserCreate) -> User:
    # 唯一性检查
    if db.query(User).filter(User.username == req.username).first():
        raise ValueError("用户名已存在")
    # 明文密码直接存（后续再改成哈希）
    user = User(username=req.username, password=req.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# ---- 登录 ----
def authenticate_user(db: Session, req: UserLogin):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or user.password != req.password:
        return None
    return user