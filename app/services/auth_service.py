# services/auth_service.py
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin
from app.core.security import create_access_token
from datetime import datetime, timedelta

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
    
    # 登录成功，设置在线状态
    user.status = "online"
    user.last_seen = None  # 清空最后离线时间
    db.commit()
    
    return user

# ---- 登出 ----
def logout_user(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.status = "offline"
        user.last_seen = datetime.utcnow() + timedelta(hours=8)
        db.commit()
    return user