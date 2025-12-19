from pydantic import BaseModel, Field, field_validator, field_serializer
from app.core.server_config import get_server_url


#注册
class UserRegister(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=6, max_length=128)
    phone: str = Field(pattern=r'^1[3-9]\d{9}$')

#登录
class UserLogin(BaseModel):
    username: str | None = Field(None, min_length=1, max_length=32)
    phone: str | None = Field(None, pattern=r'^1[3-9]\d{9}$')
    password: str

    @field_validator('password', mode='after')
    @classmethod
    def check_user_or_phone(cls, v, info):
        # 在所有字段验证后检查
        data = info.data
        username = data.get('username')
        phone = data.get('phone')
        
        if username is None and phone is None:
            raise ValueError('用户名或手机号必须填写一个')
        if username is not None and phone is not None:
            raise ValueError('用户名与手机号只能填写一个')
        return v

#返回给前端展示用
class UserResponse(BaseModel):
    id: int
    username: str
    avatar: str | None = None
    bio: str | None = None
    phone: str | None = None  

    @field_serializer('avatar')
    def serialize_avatar(self, avatar: str | None) -> str | None:
        """将相对路径转换为完整 URL"""
        if avatar and not avatar.startswith('http'):
            return f"{get_server_url()}{avatar}"
        return avatar

    class Config:
        from_attributes = True

#搜索用的
class UserSearchOut(BaseModel):
    id: int
    username: str
    avatar: str | None = None
    bio: str | None = None
    phone: str | None = None  

    @field_serializer('avatar')
    def serialize_avatar(self, avatar: str | None) -> str | None:
        """将相对路径转换为完整 URL"""
        if avatar and not avatar.startswith('http'):
            return f"{get_server_url()}{avatar}"
        return avatar

    class Config:
        from_attributes = True

#JWT
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"