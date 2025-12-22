from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from typing import List
from app.core.server_config import get_server_url


# 创建群消息
class GroupMessageCreate(BaseModel):
    group_id: int
    content: str
    msg_type: int = Field(default=1, ge=1)  # 1-文本 2-图片 3-文件 4-撤回


# 群消息响应
class GroupMessageResponse(BaseModel):
    id: int
    group_id: int
    sender_id: int
    content: str
    msg_type: int
    is_read: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer('content')
    def serialize_content(self, content: str) -> str:
        """如果是图片或文件消息，将相对路径转换为完整 URL"""
        # msg_type: 1=文本, 2=图片, 3=文件, 4=撤回
        # 只有图片和文件需要转换URL
        if self.msg_type in [2, 3] and content and not content.startswith('http'):
            return f"{get_server_url()}{content}"
        return content

    class Config:
        from_attributes = True


# 群消息分页
class GroupMessagePage(BaseModel):
    items: List[GroupMessageResponse]
    has_more: bool
    last_id: int | None
