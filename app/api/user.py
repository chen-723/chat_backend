# 用户资料管理（头像、签名、手机号等）
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
from sqlalchemy.orm import Session
from app.db.database import get_db
import shutil, uuid, os
from app.schemas.user import UserResponse
from app.core.dependencies import get_current_user
from app.models.user import User

# router = APIRouter(prefix="/users", tags=["users"])
router = APIRouter()

AVATAR_DIR = "static/avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)



@router.put("/me/avatar", response_model=UserResponse)
def updata_avatar(
    avatar: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)

):
    if avatar.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(400, "只能上传jpg.png哦~")
    
    ext= avatar.filename.split(".")[-1]
    file_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(AVATAR_DIR, file_name)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(avatar.file, f)

    current_user.avatar = f"/{AVATAR_DIR}/{file_name}"
    db.commit()
    db.refresh(current_user)

    return current_user