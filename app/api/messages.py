from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.messages import MessageCreate, MessageResponse, Messagepage, UploadResponse
from app.services import messages_service as message_service

router = APIRouter()


@router.post("/send", response_model=MessageResponse, status_code=201)
async def send_message(
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    发送消息
    
    Body:
        - receiver_id: 接收者ID
        - content: 消息内容
        - msg_type: 消息类型 (1-文本, 2-图片, 3-文件)
    """
    try:
        message = await message_service.send_message_async(db, current_user.id, message_data)
        return message
    except Exception as e:
        raise HTTPException(500, detail=f"发送消息失败: {str(e)}")
    
@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    通用文件上传（图片、语音、普通文件）
    返回静态地址，文件名用 UUID 防止冲突
    """
    import uuid, os
    from pathlib import Path

    UPLOAD_DIR = Path("static/upload")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename).suffix
    name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / name

    with file_path.open("wb") as f:
        f.write(await file.read())

    return UploadResponse(url=f"/static/upload/{name}")


@router.get("/history/{peer_user_id}", response_model=Messagepage)
def get_chat_history(
    peer_user_id: int,
    last_id: Optional[int] = Query(None, description="上次最后一条消息ID，用于分页"),
    limit: int = Query(99, ge=1, le=100, description="每页条数，默认99"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取与某个用户的聊天历史（分页）
    
    Path:
        - peer_user_id: 对方用户ID
    
    Query:
        - last_id: 上次最后一条消息ID（可选，用于分页）
        - limit: 每页条数（默认20，最大100）
    """
    try:
        return message_service.get_chat_history(
            db, 
            current_user.id, 
            peer_user_id, 
            last_id, 
            limit
        )
    except Exception as e:
        raise HTTPException(500, detail=f"获取聊天历史失败: {str(e)}")


@router.get("/unread/{peer_user_id}")
def get_unread_count(
    peer_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取与某个用户的未读消息数
    
    Path:
        - peer_user_id: 对方用户ID
    """
    count = message_service.get_unread_count(db, current_user.id, peer_user_id)
    return {"peer_user_id": peer_user_id, "unread_count": count}


@router.get("/unread")
def get_all_unread_counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户与所有联系人的未读消息数（聚合）
    
    Returns:
        - total: 总未读数
        - by_user: 每个用户的未读数 {user_id: count}
    """
    total = message_service.get_total_unread_count(db, current_user.id)
    by_user = message_service.get_unread_counts_by_user(db, current_user.id)
    
    return {
        "total": total,
        "by_user": by_user
    }


@router.post("/read/{peer_user_id}")
async def mark_messages_as_read(
    peer_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    标记与某个用户的所有消息为已读
    
    Path:
        - peer_user_id: 对方用户ID
    
    说明：
        前端进入聊天页面时调用此接口，批量标记消息为已读
    """
    try:
        updated_count = await message_service.mark_as_read_async(db, current_user.id, peer_user_id)
        return {
            "msg": "标记成功",
            "peer_user_id": peer_user_id,
            "updated_count": updated_count
        }
    except Exception as e:
        raise HTTPException(500, detail=f"标记已读失败: {str(e)}")


@router.delete("/{message_id}")
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除/撤回消息
    
    Path:
        - message_id: 消息ID
    
    说明：
        仅消息发送者可以撤回自己的消息
    """
    success = message_service.delete_message(db, message_id, current_user.id)
    
    if not success:
        raise HTTPException(404, detail="消息不存在或无权限撤回")
    
    return {"msg": "消息已撤回", "message_id": message_id}


@router.get("/search")
def search_messages(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(50, ge=1, le=100, description="返回结果数量限制，默认50"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    搜索聊天记录
    
    Query:
        - keyword: 搜索关键词（消息内容）
        - limit: 返回结果数量（默认50，最大100）
    
    Returns:
        匹配的消息列表，包含私聊和群聊消息，按时间倒序
        每条消息包含：
        - 消息内容和类型
        - 发送者信息
        - 会话信息（私聊对方/群组信息）
        - 时间戳
    
    说明：
        仅搜索与当前用户相关的消息（私聊双方包含自己，或群聊中自己是成员）
    """
    try:
        return message_service.search_messages(db, current_user.id, keyword, limit)
    except Exception as e:
        raise HTTPException(500, detail=f"搜索消息失败: {str(e)}")
