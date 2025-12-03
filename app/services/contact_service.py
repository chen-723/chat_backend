# services/contact_service.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from app.models.contact import Contact
from app.models.user import User
from app.schemas.contact import ContactResponse


def get_contacts(db: Session, user_id: int) -> list[ContactResponse]:
    """
    先只做“联系人列表”，消息相关字段全部兜底。
    """
    # 一次性把联系人及其对应的 user 对象全拉出来
    stmt = (
        select(Contact)
        .where(Contact.user_id == user_id)
        .options(joinedload(Contact.contact_user))
        .order_by(Contact.is_favorite.desc(), Contact.created_at.desc())
    )
    contacts = db.scalars(stmt).unique().all()

    # 拼 schema，返回完整的头像 URL
    return [
        ContactResponse(
            id=c.id,
            name=c.contact_user.username,
            avatar=f"http://localhost:8000{c.contact_user.avatar}" if c.contact_user.avatar else None,
            status=getattr(c.contact_user, 'status', 'offline') or "offline",
            lastSeen=c.contact_user.last_seen.isoformat() if hasattr(c.contact_user, 'last_seen') and c.contact_user.last_seen else None,
            lastMegTime=None,      # 暂无消息表
            lastMeg=None,          # 暂无消息表
            count=0,               # 暂无消息表
            is_favorite=c.is_favorite,
        )
        for c in contacts
    ]

def add_contact(db: Session, user_id: int, contact_user_id: int):
    """添加联系人"""
    # 检查是否已存在
    # 创建双向联系人关系
    pass

def remove_contact(db: Session, user_id: int, contact_user_id: int):
    """删除联系人"""
    pass

def toggle_favorite(db: Session, user_id: int, contact_user_id: int):
    """切换特别关心"""
    pass

def get_favorites(db: Session, user_id: int):
    """获取特别关心列表"""
    pass