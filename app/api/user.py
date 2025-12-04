# 用户资料管理（头像、签名、手机号等）
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.database import get_db
import shutil, uuid, os
from app.schemas.user import UserResponse, UserSearchOut
from app.core.dependencies import get_current_user
from app.models.user import User
from pydantic import BaseModel, Field

router = APIRouter()

AVATAR_DIR = "static/avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)

class BioUpdate(BaseModel):
    bio: str | None = Field(None, max_length=255)

class UsernameUpdate(BaseModel):
    username: str = Field(..., min_length=1, max_length=16)


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


@router.put("/me/bio", response_model=UserResponse)
def updata_bio(
    payload: BioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.bio = payload.bio
    db.commit()
    db.refresh(current_user)
    return current_user

@router.put("/me/username", response_model=UserResponse)
def update_username(
    payload: UsernameUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.username = payload.username
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/search", response_model=list[UserSearchOut])
def search_users(
    q: str = Query(min_length=1, max_length=20),
    db: Session = Depends(get_db)
):
    return (
        db.query(User)
        .filter(func.lower(User.username).like(f"{q.lower()}%"))
        .limit(5)
        .all()
    )