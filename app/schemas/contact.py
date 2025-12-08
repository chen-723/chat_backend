from pydantic import BaseModel
from datetime import datetime

class ContactCreate(BaseModel):
    contact_user_id: int

class ContactResponse(BaseModel):
    id: int  # 联系人关系表 ID
    user_id: int  # 联系人的真实用户 ID
    name: str  # 联系人用户名
    avatar: str | None
    status: str  # "online" | "offline"
    bio: str | None = None
    lastSeen: str | None
    lastMegTime: str | None
    lastMeg: str | None
    count: int | None  # 未读消息数
    is_favorite: bool
    
    class Config:
        from_attributes = True