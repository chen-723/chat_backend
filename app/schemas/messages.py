from pydantic import BaseModel
from datetime import datetime
from typing import List

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

    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    url: str 

class Messagepage (BaseModel):
    items : List[MessageResponse]
    has_more: bool
    last_id : int |None