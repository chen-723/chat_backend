# services/message_service.py
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, func
from app.models.messages import Messages
from app.schemas.messages import MessageCreate, MessageResponse, Messagepage
from app.websocket.manager import manager


# --------------------------------------------------
# 发送消息
# --------------------------------------------------
async def send_message_async(
    db: Session,
    sender_id: int,
    message_data: MessageCreate
) -> Messages:
    new_message = Messages(
        sender_id=sender_id,
        receiver_id=message_data.receiver_id,
        content=message_data.content,
        msg_type=message_data.msg_type,
        is_read=False
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    # 推送消息给在线接收方
    if manager.is_online(message_data.receiver_id):
        message_response = MessageResponse.model_validate(new_message)
        await manager.send_personal_message(
            message_data.receiver_id,
            {
                "type": "new_message",
                "data": message_response.model_dump(mode='json')
            }
        )
    
    return new_message


# --------------------------------------------------
# 获取聊天历史（分页）
# --------------------------------------------------
def get_chat_history(
    db: Session,
    current_user_id: int,
    peer_user_id: int,
    last_id: Optional[int] = None,
    limit: int = 99
) -> Messagepage:
    query = db.query(Messages).filter(
        or_(
            and_(Messages.sender_id == current_user_id, Messages.receiver_id == peer_user_id),
            and_(Messages.sender_id == peer_user_id, Messages.receiver_id == current_user_id)
        )
    )
    if last_id:
        query = query.filter(Messages.id < last_id)

    messages = query.order_by(desc(Messages.created_at)).limit(limit + 1).all()

    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]

    last_message_id = messages[-1].id if messages else None
    return Messagepage(
        items=[MessageResponse.model_validate(msg) for msg in messages],
        has_more=has_more,
        last_id=last_message_id
    )


# --------------------------------------------------
# 获取与某人的未读数
# --------------------------------------------------
def get_unread_count(
    db: Session,
    current_user_id: int,
    peer_user_id: int
) -> int:
    return db.query(Messages).filter(
        Messages.receiver_id == current_user_id,
        Messages.sender_id == peer_user_id,
        Messages.is_read == False
    ).count()


# --------------------------------------------------
# 标记与某人的所有消息为已读
# --------------------------------------------------
async def mark_as_read_async(
    db: Session,
    current_user_id: int,
    peer_user_id: int
) -> int:
    updated_count = db.query(Messages).filter(
        Messages.receiver_id == current_user_id,
        Messages.sender_id == peer_user_id,
        Messages.is_read == False
    ).update({"is_read": True}, synchronize_session=False)
    db.commit()
    
    # 推送已读回执给对方
    if updated_count > 0 and manager.is_online(peer_user_id):
        await manager.send_personal_message(
            peer_user_id,
            {
                "type": "read_receipt",
                "data": {
                    "reader_id": current_user_id,
                    "count": updated_count
                }
            }
        )
    
    return updated_count


# --------------------------------------------------
# 获取当前用户总未读数
# --------------------------------------------------
def get_total_unread_count(
    db: Session,
    current_user_id: int
) -> int:
    return db.query(Messages).filter(
        Messages.receiver_id == current_user_id,
        Messages.is_read == False
    ).count()


# --------------------------------------------------
# 获取与每个联系人的未读数聚合
# --------------------------------------------------
def get_unread_counts_by_user(
    db: Session,
    current_user_id: int
) -> dict[int, int]:
    rows = db.query(
        Messages.sender_id,
        func.count(Messages.id).label("unread_count")
    ).filter(
        Messages.receiver_id == current_user_id,
        Messages.is_read == False
    ).group_by(Messages.sender_id).all()
    return {sender_id: cnt for sender_id, cnt in rows}


# --------------------------------------------------
# 删除/撤回消息（仅发送者可操作）
# --------------------------------------------------
def delete_message(
    db: Session,
    message_id: int,
    user_id: int
) -> bool:
    msg = db.query(Messages).filter(
        Messages.id == message_id,
        Messages.sender_id == user_id
    ).first()
    if not msg:
        return False

    # 软撤回：标记类型+替换内容
    msg.msg_type = 4
    msg.content = "[消息已撤回]"
    db.commit()
    # TODO: 推送撤回通知
    return True


# --------------------------------------------------
# 搜索聊天记录（私聊+群聊）
# --------------------------------------------------
def search_messages(
    db: Session,
    current_user_id: int,
    keyword: str,
    limit: int = 50
) -> list[dict]:
    """
    搜索与当前用户相关的聊天记录
    返回格式：
    [
        {
            "message_id": int,
            "content": str,
            "msg_type": int,
            "created_at": datetime,
            "chat_type": "private" | "group",
            "sender": {"id": int, "username": str, "avatar": str},
            "chat_info": {
                # 私聊时：对方用户信息
                "peer_user_id": int,
                "peer_username": str,
                "peer_avatar": str,
                # 群聊时：群组信息
                "group_id": int,
                "group_name": str,
                "group_avatar": str
            }
        }
    ]
    """
    from app.models.group_messages import GroupMessage
    from app.models.groups import Group
    from app.models.group_members import GroupMember
    from app.models.user import User
    
    results = []
    
    # 1. 搜索私聊消息
    private_messages = db.query(Messages, User).join(
        User, Messages.sender_id == User.id
    ).filter(
        or_(
            Messages.sender_id == current_user_id,
            Messages.receiver_id == current_user_id
        ),
        Messages.content.like(f"%{keyword}%"),
        Messages.msg_type != 4  # 排除已撤回的消息
    ).order_by(desc(Messages.created_at)).limit(limit).all()
    
    for msg, sender in private_messages:
        # 确定对方是谁
        peer_user_id = msg.receiver_id if msg.sender_id == current_user_id else msg.sender_id
        peer_user = db.query(User).filter(User.id == peer_user_id).first()
        
        results.append({
            "message_id": msg.id,
            "content": msg.content,
            "msg_type": msg.msg_type,
            "created_at": msg.created_at,
            "chat_type": "private",
            "sender": {
                "id": sender.id,
                "username": sender.username,
                "avatar": sender.avatar
            },
            "chat_info": {
                "peer_user_id": peer_user.id if peer_user else None,
                "peer_username": peer_user.username if peer_user else "未知用户",
                "peer_avatar": peer_user.avatar if peer_user else None
            }
        })
    
    # 2. 搜索群聊消息（仅搜索用户加入的群）
    group_messages = db.query(GroupMessage, User, Group).join(
        User, GroupMessage.sender_id == User.id
    ).join(
        Group, GroupMessage.group_id == Group.id
    ).join(
        GroupMember, and_(
            GroupMember.group_id == GroupMessage.group_id,
            GroupMember.user_id == current_user_id
        )
    ).filter(
        GroupMessage.content.like(f"%{keyword}%"),
        GroupMessage.msg_type != 4  # 排除已撤回的消息
    ).order_by(desc(GroupMessage.created_at)).limit(limit).all()
    
    for msg, sender, group in group_messages:
        results.append({
            "message_id": msg.id,
            "content": msg.content,
            "msg_type": msg.msg_type,
            "created_at": msg.created_at,
            "chat_type": "group",
            "sender": {
                "id": sender.id,
                "username": sender.username,
                "avatar": sender.avatar
            },
            "chat_info": {
                "group_id": group.id,
                "group_name": group.name,
                "group_avatar": group.avatar
            }
        })
    
    # 3. 按时间倒序排序并限制数量
    results.sort(key=lambda x: x["created_at"], reverse=True)
    return results[:limit]