from sqlalchemy import Column, Integer, ForeignKey, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 当前用户
    contact_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 联系人
    is_favorite = Column(Boolean, default=False)  # 是否特别关心
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系（可选，方便查询）
    owner = relationship("User", foreign_keys=[user_id], backref="contact_records")
    contact_user = relationship("User", foreign_keys=[contact_user_id])
