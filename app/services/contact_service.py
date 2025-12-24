# services/contact_service.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, delete, desc, func, and_
from app.models.contact import Contact
from app.models.user import User
from app.models.messages import Messages
from app.schemas.contact import ContactResponse
from datetime import datetime, timezone
from app.core.server_config import get_server_url

from fastapi import HTTPException, status

def _format_time_ago(dt: datetime) -> str:
    """将时间转换为相对时间格式，如 '15 min ago'"""
    # MySQL 存储的是本地时间（东八区），直接用本地时间计算
    now = datetime.now()
    
    # 如果 dt 有时区信息，转换为 naive datetime
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    
    diff = now - dt
    seconds = int(diff.total_seconds())
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:  # 小于1小时
        minutes = seconds // 60
        return f"{minutes} min ago"
    elif seconds < 86400:  # 小于1天
        hours = seconds // 3600
        return f"{hours}h ago"
    elif seconds < 604800:  # 小于7天
        days = seconds // 86400
        return f"{days}d ago"
    elif seconds < 2592000:  # 小于30天
        weeks = seconds // 604800
        return f"{weeks}w ago"
    else:
        months = seconds // 2592000
        return f"{months}mo ago"

def _to_contact_resp(contact: Contact, last_msg: Messages | None = None, unread_cnt: int = 0) -> ContactResponse:
    u = contact.contact_user
    return ContactResponse(
        id=contact.id,
        user_id=contact.contact_user_id,  # 添加真实用户 ID
        name=u.username,
        avatar=f"{get_server_url()}{u.avatar}" if u.avatar else None,
        status=getattr(u, "status", "offline") or "offline",
        bio=u.bio,
        lastSeen=u.last_seen.isoformat() if u.last_seen else None,
        lastMegTime=_format_time_ago(last_msg.created_at) if last_msg else None,
        lastMeg=last_msg.content if last_msg else None,
        count=unread_cnt,
        is_favorite=contact.is_favorite,
    )

def get_contacts(db: Session, user_id: int) -> list[ContactResponse]:
    # 获取所有联系人（预加载 contact_user）
    stmt = (
        select(Contact)
        .where(Contact.user_id == user_id)
        .options(joinedload(Contact.contact_user))
        .order_by(Contact.is_favorite.desc(), Contact.created_at.desc())
    )
    contacts = db.scalars(stmt).unique().all()
    
    result = []
    for contact in contacts:
        contact_user_id = contact.contact_user_id
        
        # 获取最新一条消息（对方发给我的）
        last_msg = db.scalar(
            select(Messages)
            .where(
                Messages.sender_id == contact_user_id,
                Messages.receiver_id == user_id
            )
            .order_by(desc(Messages.created_at))
            .limit(1)
        )
        
        # 获取未读消息数
        unread_cnt = db.scalar(
            select(func.count(Messages.id))
            .where(
                Messages.sender_id == contact_user_id,
                Messages.receiver_id == user_id,
                Messages.is_read == False
            )
        ) or 0
        
        result.append(_to_contact_resp(contact, last_msg, unread_cnt))
    
    # 按是否特别关心和最新消息时间排序
    result.sort(key=lambda x: (
        not x.is_favorite,
        x.lastMegTime is None,
        x.lastMegTime or ""
    ), reverse=False)
    
    return result


def add_contact(db: Session, user_id: int, contact_user_id: int) -> ContactResponse:
    if user_id == contact_user_id:
        raise HTTPException(400, "不能添加自己为联系人")

    exists = db.scalar(select(Contact).where(
        Contact.user_id == user_id,
        Contact.contact_user_id == contact_user_id))
    if exists:
        raise HTTPException(400, "联系人已存在")

    # 双向插入
    forward = Contact(user_id=user_id, contact_user_id=contact_user_id)
    reverse = Contact(user_id=contact_user_id, contact_user_id=user_id)
    db.add_all([forward, reverse])
    db.commit()
    
    # 刷新并加载关联的 contact_user
    db.refresh(forward)
    stmt = select(Contact).where(Contact.id == forward.id).options(joinedload(Contact.contact_user))
    forward = db.scalar(stmt)
    
    return _to_contact_resp(forward)


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

def toggle_favorite(db: Session, user_id: int, contact_user_id: int) -> ContactResponse:
    """切换特别关心"""
    # 查询时预加载 contact_user 关系
    stmt = (
        select(Contact)
        .where(
            (Contact.user_id == user_id) & (Contact.contact_user_id == contact_user_id)
        )
        .options(joinedload(Contact.contact_user))
    )
    contact = db.scalar(stmt)

    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    
    # 翻转 is_favorite 状态
    contact.is_favorite = not contact.is_favorite
    db.commit()
    
    # 获取最新消息和未读数
    last_msg = db.scalar(
        select(Messages)
        .where(
            Messages.sender_id == contact_user_id,
            Messages.receiver_id == user_id
        )
        .order_by(desc(Messages.created_at))
        .limit(1)
    )
    
    unread_cnt = db.scalar(
        select(func.count(Messages.id))
        .where(
            Messages.sender_id == contact_user_id,
            Messages.receiver_id == user_id,
            Messages.is_read == False
        )
    ) or 0

    return _to_contact_resp(contact, last_msg, unread_cnt)

def get_contact_detail(db: Session, user_id: int, contact_user_id: int) -> ContactResponse:
    """获取指定联系人详情"""
    # 查询联系人关系并预加载 contact_user
    stmt = (
        select(Contact)
        .where(
            (Contact.user_id == user_id) & (Contact.contact_user_id == contact_user_id)
        )
        .options(joinedload(Contact.contact_user))
    )
    contact = db.scalar(stmt)

    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")
    
    # 获取最新消息
    last_msg = db.scalar(
        select(Messages)
        .where(
            Messages.sender_id == contact_user_id,
            Messages.receiver_id == user_id
        )
        .order_by(desc(Messages.created_at))
        .limit(1)
    )
    
    # 获取未读消息数
    unread_cnt = db.scalar(
        select(func.count(Messages.id))
        .where(
            Messages.sender_id == contact_user_id,
            Messages.receiver_id == user_id,
            Messages.is_read == False
        )
    ) or 0

    return _to_contact_resp(contact, last_msg, unread_cnt)