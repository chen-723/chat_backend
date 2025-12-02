from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin
from app.core.security import create_access_token

# ---- 注册 ----
def register_user(db: Session, req: UserRegister) -> User:
    # 唯一性检查
    if db.query(User).filter(User.username == req.username).first():
        raise ValueError("用户名已存在")
    if db.query(User).filter(User.phone == req.phone).first():
        raise ValueError("手机号已存在")
    # 明文密码直接存（后续再改成哈希）
    user = User(username=req.username, password=req.password, phone=req.phone)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# ---- 登录 ----
def authenticate_user(db: Session, req: UserLogin):
    # 根据用户名或手机号查询
    if req.username:
        user = db.query(User).filter(User.username == req.username).first()
    elif req.phone:
        user = db.query(User).filter(User.phone == req.phone).first()
    else:
        return None
    
    if not user or user.password != req.password:
        return None
    return user