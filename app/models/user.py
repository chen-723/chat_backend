from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id       = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(32), unique=True, nullable=False)
    password = Column(String(128), nullable=False)   # 先明文，后面再改hashed_password
    avatar      = Column(String(256), nullable=True)        # 头像 url
    bio         = Column(String(256), nullable=True)        # 个性签名
    phone       = Column(String(20), unique=True, nullable=False)  # 手机号
    status      = Column(String(20), default="offline")     # 在线状态
    last_seen   = Column(DateTime, nullable=True)           # 最后登录时间