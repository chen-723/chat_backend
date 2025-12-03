from pydantic import BaseModel
from datetime import datetime

class ContactCreate(BaseModel):
    contact_user_id: int

class ContactResponse(BaseModel):
    id: int
    name: str  # 联系人用户名
    avatar: str | None
    status: str  # "online" | "offline"
    lastSeen: str | None
    lastMegTime: str | None
    lastMeg: str | None
    count: int | None  # 未读消息数
    is_favorite: bool
    
    class Config:
        from_attributes = True