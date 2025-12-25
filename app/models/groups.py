from sqlalchemy import Column, DateTime, Integer, String, func
from app.db.database import Base

#群表，描述群的基本信息
class Group(Base):
    __tablename__ = "groups"

    #群ID
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    #群名
    name = Column(String(50), nullable=False, index=True)
    #群头像
    avatar = Column(String(256), nullable=True)
    #群主id
    owner_id = Column(Integer, nullable=False, index=True)
    #描述
    description = Column(String(256), nullable=True)
    #创建时间
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    #群人数
    member_count = Column(Integer, nullable=False, default=1)
