# services/contact_service.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select,delete
from app.models.contact import Contact
from app.models.user import User
from app.schemas.contact import ContactResponse

from fastapi import HTTPException, status

def _to_contact_resp(contact: Contact) -> ContactResponse:
    u = contact.contact_user
    return ContactResponse(
        id=contact.id,
        name=u.username,
        avatar=f"http://localhost:8000{u.avatar}" if u.avatar else None,
        status=getattr(u, "status", "offline") or "offline",
        lastSeen=u.last_seen.isoformat() if u.last_seen else None,
        lastMegTime=None,
        lastMeg=None,
        count=0,
        is_favorite=contact.is_favorite,
    )


def get_contacts(db: Session, user_id: int) -> list[ContactResponse]:
    # 一次性把联系人及其对应的 user 对象全拉出来
    stmt = (
        select(Contact)
        .where(Contact.user_id == user_id)
        .options(joinedload(Contact.contact_user))
        .order_by(Contact.is_favorite.desc(), Contact.created_at.desc())
    )
    return [_to_contact_resp(c) for c in db.scalars(stmt).unique().all()]



def add_contact(db: Session, user_id: int, contact_user_id: int) -> ContactResponse:
    if user_id == contact_user_id:
        raise HTTPException(400, "不能添加自己为联系人")

    exists = db.scalar(select(Contact).where_by(user_id=user_id, contact_user_id=contact_user_id))
    if exists:
        raise HTTPException(400, "联系人已存在")

    # 双向插入
    forward = Contact(user_id=user_id, contact_user_id=contact_user_id)
    reverse = Contact(user_id=contact_user_id, contact_user_id=user_id)
    db.add_all([forward, reverse])
    db.commit()
    return _to_contact_resp(forward)   # 只把“正向”记录返回即可



def remove_contact(db: Session, user_id: int, contact_user_id: int) -> None:
    """双向删除，无返回值"""
    db.execute(
        delete(Contact).where(
            (Contact.user_id == user_id) & (Contact.contact_user_id == contact_user_id)
        )
    )
    db.execute(
        delete(Contact).where(
            (Contact.user_id == contact_user_id) & (Contact.contact_user_id == user_id)
        )
    )
    db.commit()

def toggle_favorite(db: Session, user_id: int, contact_user_id: int):
    """切换特别关心"""
    pass

def get_favorites(db: Session, user_id: int):
    """获取特别关心列表"""
    pass