from sqlalchemy import Column, DateTime, Integer, String
from app.db.database import Base


class GroupMember(Base):
    __tablename__ = "group_members"

    #成员ID
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    #群ID
    group_id = Column(Integer, nullable=False, index=True)
    #用户ID
    user_id = Column(Integer, nullable=False, index=True)
    #角色
    role = Column(Integer, nullable=False, default=3) #1-群主 2-管理员 3-普通成员
    #加入时间
    joined_at = Column(DateTime, nullable=False)