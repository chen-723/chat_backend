from pydantic import BaseModel, Field
from datetime import datetime


# 添加群成员
class GroupMemberAdd(BaseModel):
    group_id: int
    user_id: int
    role: int = Field(default=3, ge=1, le=3)  # 1-群主 2-管理员 3-普通成员


# 更新群成员角色
class GroupMemberRoleUpdate(BaseModel):
    role: int = Field(ge=1, le=3)  # 1-群主 2-管理员 3-普通成员


# 群成员响应
class GroupMemberResponse(BaseModel):
    id: int
    group_id: int
    user_id: int
    role: int
    joined_at: datetime

    class Config:
        from_attributes = True
