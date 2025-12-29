#注册登录部分专用的
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.user import UserRegister, UserLogin, UserResponse, Token
from app.services.auth_service import register_user, authenticate_user, logout_user
from app.core.dependencies import get_current_user
from app.models.user import User
from app.core.security import create_access_token

router = APIRouter()

# 1. 注册
@router.post("/register", response_model=UserResponse, status_code=201)
def register(req: UserRegister, db: Session = Depends(get_db)):
    try:
        return register_user(db, req)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))

# 2. 登录
@router.post("/login", response_model=Token)
def login(req: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, req)
    if not user:
        raise HTTPException(401, detail="用户名或密码错误")
    token = create_access_token({"user_id": user.id})
    return Token(access_token=token, token_type="bearer")

# 3. 测试 token
@router.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user

# 4. 登出
@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logout_user(db, current_user.id)
    return {"msg": "登出成功"}

# 5. 设置在线状态
@router.put("/me/status")
def update_status(
    status: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动设置用户在线状态"""
    from datetime import datetime, timedelta
    
    new_status = status.get("status")
    if new_status not in ["online", "offline"]:
        raise HTTPException(400, detail="状态必须是 online 或 offline")
    
    current_user.status = new_status
    if new_status == "offline":
        current_user.last_seen = datetime.utcnow() + timedelta(hours=8)
    else:
        current_user.last_seen = None
    
    db.commit()
    return {"msg": f"状态已更新为 {new_status}"}