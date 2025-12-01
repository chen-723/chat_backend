from pydantic import BaseModel, Field


#注册
class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=6, max_length=128)

#登录
class UserLogin(BaseModel):
    username: str
    password: str

#返回给前端
class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True

#JWT
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"