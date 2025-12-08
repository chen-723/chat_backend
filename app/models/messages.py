from sqlalchemy import Column, Integer, String, Text, SmallInteger, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class Messages(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 发送方 & 接收方（私聊场景）
    sender_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 消息内容
    content = Column(Text, nullable=False)

    # 消息类型：1-文本 2-图片 3-文件 4-撤回 ...
    msg_type = Column(SmallInteger, default=1, nullable=False)

    # 已读标记
    is_read = Column(Boolean, default=False, nullable=False)

    # 创建 & 更新（撤回/编辑时更新）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ORM 关系（可选，方便快速查用户）
    sender   = relationship("User", foreign_keys=[sender_id],   backref="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], backref="received_messages")