from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.groups import GroupCreate, GroupUpdate, GroupResponse
from app.schemas.group_members import GroupMemberRoleUpdate, GroupMemberResponse
from app.schemas.group_messages import GroupMessageCreate, GroupMessageResponse, GroupMessagePage
from app.services import group_service
import shutil, uuid, os

router = APIRouter()

AVATAR_DIR = "static/avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)


# ==================== 群组管理接口 ====================

@router.post("/create", response_model=GroupResponse, status_code=201)
def create_group(
    group_data: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建群组
    
    Body:
        - name: 群名称（必填，1-50字符）
        - avatar: 群头像URL（可选）
        - description: 群描述（可选，最多256字符）
    
    说明：
        创建者自动成为群主
    """
    try:
        group = group_service.create_group(db, group_data, current_user.id)
        return group
    except Exception as e:
        raise HTTPException(500, detail=f"创建群组失败: {str(e)}")


@router.get("/", response_model=list[GroupResponse])
def get_my_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取我加入的所有群组列表
    
    Returns:
        群组列表，按创建时间倒序
    """
    try:
        return group_service.get_user_groups(db, current_user.id)
    except Exception as e:
        raise HTTPException(500, detail=f"获取群组列表失败: {str(e)}")


@router.get("/search", response_model=list[GroupResponse])
def search_groups(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    搜索我加入的群组
    
    Query:
        - keyword: 搜索关键词（群名称）
    
    Returns:
        匹配的群组列表，仅返回当前用户已加入的群组
    """
    try:
        return group_service.search_user_groups(db, current_user.id, keyword)
    except Exception as e:
        raise HTTPException(500, detail=f"搜索群组失败: {str(e)}")


@router.get("/{group_id}", response_model=GroupResponse)
def get_group_detail(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取群组详情
    
    Path:
        - group_id: 群组ID
    
    说明：
        仅群成员可查看
    """
    return group_service.get_group_detail(db, group_id, current_user.id)


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    update_data: GroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新群组信息
    
    Path:
        - group_id: 群组ID
    
    Body:
        - name: 群名称（可选）
        - avatar: 群头像URL（可选）
        - description: 群描述（可选）
    
    说明：
        仅群主和管理员可操作
    """
    return group_service.update_group(db, group_id, current_user.id, update_data)


@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    解散群组
    
    Path:
        - group_id: 群组ID
    
    说明：
        仅群主可操作
    """
    group_service.delete_group(db, group_id, current_user.id)
    return {"msg": "群组已解散", "group_id": group_id}


@router.post("/{group_id}/avatar")
def upload_group_avatar(
    group_id: int,
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传群头像
    
    Path:
        - group_id: 群组ID
    
    说明：
        仅群主和管理员可操作，头像保存到 avatars 目录（不会被定期清理）
    """
    if avatar.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(400, "只能上传 JPG 或 PNG 格式的图片")
    
    ext = avatar.filename.split(".")[-1]
    file_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(AVATAR_DIR, file_name)

    with open(file_path, "wb") as f:
        shutil.copyfileobj(avatar.file, f)

    avatar_url = f"/static/avatars/{file_name}"
    
    # 更新群头像
    from app.schemas.groups import GroupUpdate
    group = group_service.update_group(
        db, 
        group_id, 
        current_user.id, 
        GroupUpdate(avatar=avatar_url)
    )
    
    return {"url": avatar_url, "group": group}




# ==================== 群成员管理接口 ====================

@router.get("/{group_id}/members")
def get_group_members(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取群成员列表
    
    Path:
        - group_id: 群组ID
    
    Returns:
        成员列表，包含用户信息和角色，按角色和加入时间排序
    
    说明：
        仅群成员可查看
    """
    return group_service.get_group_members(db, group_id, current_user.id)


@router.post("/{group_id}/members/{user_id}", response_model=GroupMemberResponse, status_code=201)
async def add_group_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    添加群成员
    
    Path:
        - group_id: 群组ID
        - user_id: 要添加的用户ID
    
    说明：
        仅群主和管理员可操作
    """
    return await group_service.add_group_member(db, group_id, current_user.id, user_id)


@router.delete("/{group_id}/members/{user_id}")
def remove_group_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    移除群成员 / 退出群聊
    
    Path:
        - group_id: 群组ID
        - user_id: 要移除的用户ID
    
    说明：
        - 群主和管理员可以移除其他成员
        - 普通成员可以移除自己（退群）
        - 群主不能退群，需要先转让群主或解散群组
    """
    group_service.remove_group_member(db, group_id, current_user.id, user_id)
    return {"msg": "操作成功", "group_id": group_id, "user_id": user_id}


@router.put("/{group_id}/members/{user_id}/role", response_model=GroupMemberResponse)
def update_member_role(
    group_id: int,
    user_id: int,
    role_data: GroupMemberRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新群成员角色
    
    Path:
        - group_id: 群组ID
        - user_id: 目标用户ID
    
    Body:
        - role: 角色（2-管理员，3-普通成员）
    
    说明：
        仅群主可操作，不能通过此接口转让群主
    """
    return group_service.update_member_role(db, group_id, current_user.id, user_id, role_data.role)


# ==================== 群消息接口 ====================

@router.post("/{group_id}/messages", response_model=GroupMessageResponse, status_code=201)
async def send_group_message(
    group_id: int,
    content: str,
    msg_type: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    发送群消息
    
    Path:
        - group_id: 群组ID
    
    Body (form-data or json):
        - content: 消息内容
        - msg_type: 消息类型（1-文本，2-图片，3-文件，默认1）
    
    说明：
        仅群成员可发送消息
    """
    message_data = GroupMessageCreate(
        group_id=group_id,
        content=content,
        msg_type=msg_type
    )
    try:
        message = await group_service.send_group_message(db, current_user.id, message_data)
        return message
    except Exception as e:
        raise HTTPException(500, detail=f"发送消息失败: {str(e)}")


@router.get("/{group_id}/messages", response_model=GroupMessagePage)
def get_group_messages(
    group_id: int,
    last_id: Optional[int] = Query(None, description="上次最后一条消息ID，用于分页"),
    limit: int = Query(99, ge=1, le=100, description="每页条数，默认30"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取群聊天记录（分页）
    
    Path:
        - group_id: 群组ID
    
    Query:
        - last_id: 上次最后一条消息ID（可选，用于分页）
        - limit: 每页条数（默认30，最大100）
    
    说明：
        仅群成员可查看
    """
    return group_service.get_group_messages(db, group_id, current_user.id, last_id, limit)


@router.get("/{group_id}/messages/unread")
def get_group_unread_count(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取群未读消息数
    
    Path:
        - group_id: 群组ID
    """
    count = group_service.get_group_unread_count(db, group_id, current_user.id)
    return {"group_id": group_id, "unread_count": count}


@router.post("/{group_id}/messages/read")
async def mark_group_messages_read(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    标记群消息为已读
    
    Path:
        - group_id: 群组ID
    
    说明：
        前端进入群聊页面时调用此接口，批量标记消息为已读
    """
    try:
        updated_count = await group_service.mark_group_messages_read(db, group_id, current_user.id)
        return {
            "msg": "标记成功",
            "group_id": group_id,
            "updated_count": updated_count
        }
    except Exception as e:
        raise HTTPException(500, detail=f"标记已读失败: {str(e)}")
