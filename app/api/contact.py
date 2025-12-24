from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.contact import ContactCreate, ContactResponse
from app.services import contact_service

router = APIRouter()

@router.get("/", response_model=list[ContactResponse])
def get_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取联系人列表"""
    return contact_service.get_contacts(db, current_user.id)

@router.post("/", status_code=201)
def add_contact(
    payload: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """添加联系人"""
    return contact_service.add_contact(db, current_user.id, payload.contact_user_id)

@router.delete("/{contact_user_id}", status_code=204)
def remove_contact(
    contact_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除联系人"""
    contact_service.remove_contact(db, current_user.id, contact_user_id)
    return {"msg": "删除成功"}


@router.patch("/{contact_user_id}/favorite")
def toggle_favorite(
    contact_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """切换特别关心"""
    return contact_service.toggle_favorite(db, current_user.id, contact_user_id)

@router.get("/{contact_user_id}", response_model=ContactResponse)
def get_contact_detail(
    contact_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定联系人详情"""
    return contact_service.get_contact_detail(db, current_user.id, contact_user_id)

# @router.get("/favorites", response_model=list[ContactResponse])
# def get_favorites(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """获取特别关心列表"""
#     return contact_service.get_favorites(db, current_user.id)
