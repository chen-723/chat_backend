from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, desc, func, and_, or_
from typing import Optional
from datetime import datetime
from fastapi import HTTPException
from app.models.groups import Group
from app.models.group_members import GroupMember
from app.models.group_messages import GroupMessage
from app.models.user import User
from app.schemas.groups import GroupCreate, GroupUpdate, GroupResponse
from app.schemas.group_members import GroupMemberAdd, GroupMemberRoleUpdate, GroupMemberResponse
from app.schemas.group_messages import GroupMessageCreate, GroupMessageResponse, GroupMessagePage
from app.websocket.manager import manager


# ==================== 群组管理 ====================

def create_group(db: Session, group_data: GroupCreate, owner_id: int) -> Group:
    """创建群组，并自动添加创建者为群主"""
    new_group = Group(
        name=group_data.name,
        avatar=group_data.avatar,
        owner_id=owner_id,
        description=group_data.description
    )
    db.add(new_group)
    db.flush()  # 获取 group.id
    
    # 添加创建者为群主
    owner_member = GroupMember(
        group_id=new_group.id,
        user_id=owner_id,
        role=1,  # 1-群主
        joined_at=datetime.now()
    )
    db.add(owner_member)
    db.commit()
    db.refresh(new_group)
    return new_group


def get_user_groups(db: Session, user_id: int) -> list[GroupResponse]:
    """获取用户加入的所有群组"""
    stmt = (
        select(Group)
        .join(GroupMember, Group.id == GroupMember.group_id)
        .where(GroupMember.user_id == user_id)
        .order_by(desc(Group.created_at))
    )
    groups = db.scalars(stmt).all()
    return [GroupResponse.model_validate(g) for g in groups]


def search_user_groups(db: Session, user_id: int, keyword: str) -> list[GroupResponse]:
    """搜索用户加入的群组（按群名称）"""
    stmt = (
        select(Group)
        .join(GroupMember, Group.id == GroupMember.group_id)
        .where(
            GroupMember.user_id == user_id,
            Group.name.like(f"%{keyword}%")
        )
        .order_by(desc(Group.created_at))
    )
    groups = db.scalars(stmt).all()
    return [GroupResponse.model_validate(g) for g in groups]


def get_group_detail(db: Session, group_id: int, user_id: int) -> GroupResponse:
    """获取群组详情（需要是群成员）"""
    # 检查是否是群成员
    member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id
        )
    )
    if not member:
        raise HTTPException(403, "您不是该群成员")
    
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(404, "群组不存在")
    
    return GroupResponse.model_validate(group)


def update_group(db: Session, group_id: int, user_id: int, update_data: GroupUpdate) -> GroupResponse:
    """更新群组信息（仅群主和管理员）"""
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(404, "群组不存在")
    
    # 检查权限
    member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id
        )
    )
    if not member or member.role not in [1, 2]:  # 1-群主 2-管理员
        raise HTTPException(403, "无权限修改群组信息")
    
    # 更新字段
    if update_data.name is not None:
        group.name = update_data.name
    if update_data.avatar is not None:
        group.avatar = update_data.avatar
    if update_data.description is not None:
        group.description = update_data.description
    
    db.commit()
    db.refresh(group)
    return GroupResponse.model_validate(group)


def delete_group(db: Session, group_id: int, user_id: int) -> None:
    """解散群组（仅群主）"""
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(404, "群组不存在")
    
    if group.owner_id != user_id:
        raise HTTPException(403, "只有群主可以解散群组")
    
    # 删除群成员和消息（如果设置了级联删除会自动处理）
    db.delete(group)
    db.commit()


# ==================== 群成员管理 ====================

def get_group_members(db: Session, group_id: int, user_id: int) -> list[dict]:
    """获取群成员列表（需要是群成员）"""
    # 检查是否是群成员
    member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id
        )
    )
    if not member:
        raise HTTPException(403, "您不是该群成员")
    
    # 获取所有成员及用户信息
    stmt = (
        select(GroupMember, User)
        .join(User, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id)
        .order_by(GroupMember.role.asc(), GroupMember.joined_at.asc())
    )
    results = db.execute(stmt).all()
    
    members = []
    for gm, user in results:
        members.append({
            "id": gm.id,
            "user_id": user.id,
            "username": user.username,
            "avatar": user.avatar,
            "role": gm.role,
            "joined_at": gm.joined_at
        })
    
    return members


async def add_group_member(db: Session, group_id: int, operator_id: int, target_user_id: int) -> GroupMemberResponse:
    """添加群成员（群主和管理员可操作）"""
    # 检查群是否存在
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(404, "群组不存在")
    
    # 检查操作者权限
    operator = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == operator_id
        )
    )
    if not operator or operator.role not in [1, 2]:
        raise HTTPException(403, "无权限添加成员")
    
    # 检查目标用户是否已在群中
    existing = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == target_user_id
        )
    )
    if existing:
        raise HTTPException(400, "用户已在群中")
    
    # 添加成员
    new_member = GroupMember(
        group_id=group_id,
        user_id=target_user_id,
        role=3,  # 3-普通成员
        joined_at=datetime.now()
    )
    db.add(new_member)
    
    # 更新群人数 +1
    group.member_count += 1
    
    db.commit()
    db.refresh(new_member)
    
    # 发送 WebSocket 通知给被添加的用户
    if manager.is_online(target_user_id):
        await manager.send_personal_message(
            target_user_id,
            {
                "type": "group_member_added",
                "data": {
                    "group_id": group_id,
                    "group_name": group.name,
                    "operator_id": operator_id
                }
            }
        )
    
    return GroupMemberResponse.model_validate(new_member)


def remove_group_member(db: Session, group_id: int, operator_id: int, target_user_id: int) -> None:
    """移除群成员（群主和管理员可操作，或自己退群）"""
    # 检查操作者权限
    operator = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == operator_id
        )
    )
    if not operator:
        raise HTTPException(403, "您不是该群成员")
    
    # 检查目标成员
    target = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == target_user_id
        )
    )
    if not target:
        raise HTTPException(404, "目标用户不在群中")
    
    # 权限检查：自己退群 或 管理员/群主踢人
    if operator_id == target_user_id:
        # 自己退群
        if operator.role == 1:
            raise HTTPException(400, "群主不能退群，请先转让群主或解散群组")
    elif operator.role not in [1, 2]:
        raise HTTPException(403, "无权限移除成员")
    
    # 获取群组并更新人数 -1
    group = db.get(Group, group_id)
    if group:
        group.member_count = max(0, group.member_count - 1)
    
    db.delete(target)
    db.commit()


def update_member_role(db: Session, group_id: int, operator_id: int, target_user_id: int, new_role: int) -> GroupMemberResponse:
    """更新群成员角色（仅群主可操作）"""
    # 检查操作者是否是群主
    operator = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == operator_id
        )
    )
    if not operator or operator.role != 1:
        raise HTTPException(403, "只有群主可以修改成员角色")
    
    # 检查目标成员
    target = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == target_user_id
        )
    )
    if not target:
        raise HTTPException(404, "目标用户不在群中")
    
    if new_role == 1:
        raise HTTPException(400, "请使用转让群主接口")
    
    target.role = new_role
    db.commit()
    db.refresh(target)
    
    return GroupMemberResponse.model_validate(target)


# ==================== 群消息管理 ====================

async def send_group_message(db: Session, sender_id: int, message_data: GroupMessageCreate) -> GroupMessage:
    """发送群消息"""
    # 检查是否是群成员
    member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == message_data.group_id,
            GroupMember.user_id == sender_id
        )
    )
    if not member:
        raise HTTPException(403, "您不是该群成员")
    
    # 创建消息
    new_message = GroupMessage(
        group_id=message_data.group_id,
        sender_id=sender_id,
        content=message_data.content,
        msg_type=message_data.msg_type,
        is_read=False
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    # 推送消息给群内所有在线成员（除了发送者）
    stmt = select(GroupMember.user_id).where(
        GroupMember.group_id == message_data.group_id,
        GroupMember.user_id != sender_id
    )
    member_ids = db.scalars(stmt).all()
    
    message_response = GroupMessageResponse.model_validate(new_message)
    for member_id in member_ids:
        if manager.is_online(member_id):
            await manager.send_personal_message(
                member_id,
                {
                    "type": "new_group_message",
                    "data": message_response.model_dump(mode='json')
                }
            )
    
    return new_message


def get_group_messages(
    db: Session,
    group_id: int,
    user_id: int,
    last_id: Optional[int] = None,
    limit: int = 99
) -> GroupMessagePage:
    """获取群聊天记录（分页）"""
    # 1. 验成员
    member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id
        )
    )
    if not member:
        raise HTTPException(403, "您不是该群成员")

    # 2. 查消息
    query = db.query(GroupMessage).filter(GroupMessage.group_id == group_id)
    if last_id:
        query = query.filter(GroupMessage.id < last_id)

    msgs = query.order_by(desc(GroupMessage.created_at)).limit(limit + 1).all()

    # 3. 组装分页
    has_more = len(msgs) > limit
    if has_more:
        msgs = msgs[:limit]

    last_message_id = msgs[-1].id if msgs else None

    return GroupMessagePage(
        items=[GroupMessageResponse.model_validate(m) for m in msgs],
        has_more=has_more,
        last_id=last_message_id
    )


def get_group_unread_count(db: Session, group_id: int, user_id: int) -> int:
    """获取群未读消息数"""
    # 检查是否是群成员
    member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id
        )
    )
    if not member:
        return 0
    
    # 统计该群中其他人发送的未读消息
    count = db.scalar(
        select(func.count(GroupMessage.id)).where(
            GroupMessage.group_id == group_id,
            GroupMessage.sender_id != user_id,
            GroupMessage.is_read == False
        )
    ) or 0
    
    return count


async def mark_group_GroupMessage_read(db: Session, group_id: int, user_id: int) -> int:
    """标记群消息为已读"""
    # 检查是否是群成员
    member = db.scalar(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id
        )
    )
    if not member:
        raise HTTPException(403, "您不是该群成员")
    
    # 标记该群中其他人发送的消息为已读
    updated_count = db.query(GroupMessage).filter(
        GroupMessage.group_id == group_id,
        GroupMessage.sender_id != user_id,
        GroupMessage.is_read == False
    ).update({"is_read": True}, synchronize_session=False)
    
    db.commit()
    return updated_count
