from pydantic import BaseModel, field_serializer
from datetime import datetime
from typing import List
from app.core.server_config import get_server_url

class MessageCreate (BaseModel):
    receiver_id : int
    content : str
    msg_type : int = 1  # 1普通文本 2图片 3文件

class MessageResponse (BaseModel):
    id : int 
    sender_id : int
    receiver_id : int
    content : str
    msg_type :int
    is_read : bool
    created_at : datetime

    @field_serializer('content')
    def serialize_content(self, content: str) -> str:
        """如果是图片或文件消息，将相对路径转换为完整 URL"""
        # msg_type: 1=文本, 2=图片, 3=文件
        # 只有图片和文件需要转换URL
        if self.msg_type in [2, 3] and content and not content.startswith('http'):
            return f"{get_server_url()}{content}"
        return content

    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    url: str 

class Messagepage (BaseModel):
    items : List[MessageResponse]
    has_more: bool
    last_id : int |None