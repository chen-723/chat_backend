from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from app.core.server_config import get_server_url


# 创建群组
class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    avatar: str | None = None
    description: str | None = Field(None, max_length=256)


# 更新群组信息
class GroupUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    avatar: str | None = None
    description: str | None = Field(None, max_length=256)


# 群组响应
class GroupResponse(BaseModel):
    id: int
    name: str
    avatar: str | None = None
    owner_id: int
    description: str | None = None
    created_at: datetime
    member_count: int

    @field_serializer('avatar')
    def serialize_avatar(self, avatar: str | None) -> str | None:
        """将相对路径转换为完整 URL"""
        if avatar and not avatar.startswith('http'):
            return f"{get_server_url()}{avatar}"
        return avatar

    class Config:
        from_attributes = True
