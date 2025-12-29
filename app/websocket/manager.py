from typing import Dict
from fastapi import WebSocket
import json
import logging
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃连接: {user_id: WebSocket}
        self.active_connections: Dict[int, WebSocket] = {}
        # 存储通话状态: {user_id: peer_user_id}
        self.active_calls: Dict[int, int] = {}
    
    async def connect(self, user_id: int, websocket: WebSocket):
        """建立连接"""
        # 如果用户已有连接，先关闭旧连接
        if user_id in self.active_connections:
            await self.close_connection(user_id)
        
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"用户 {user_id} 已连接，当前在线: {len(self.active_connections)}")
    
    async def close_connection(self, user_id: int):
        """安全关闭连接"""
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]
                await websocket.close()
            except Exception as e:
                logger.warning(f"关闭用户 {user_id} 连接时出错: {e}")
            finally:
                del self.active_connections[user_id]
    
    def disconnect(self, user_id: int):
        """断开连接（同步版本）"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"用户 {user_id} 已断开，当前在线: {len(self.active_connections)}")
    
    async def send_personal_message(self, user_id: int, message: dict):
        """发送消息给指定用户"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message, ensure_ascii=False))
                return True
            except Exception as e:
                logger.error(f"发送消息给用户 {user_id} 失败: {e}")
                self.disconnect(user_id)
                return False
        return False
    
    def is_online(self, user_id: int) -> bool:
        """检查用户是否在线"""
        return user_id in self.active_connections
    
# --------------------------------------------------
# 获取用户的在线联系人列表(新增)
    
    async def get_online_contacts(self, user_id: int, db) -> list:
        """获取用户的在线联系人列表
        
        Args:
            user_id: 用户ID
            db: 数据库会话
            
        Returns:
            在线联系人的 user_id 列表
        """
        from app.models.contact import Contact
        
        # 获取该用户的所有联系人
        contacts = db.query(Contact).filter(
            (Contact.user_id == user_id) | (Contact.contact_user_id == user_id)
        ).all()
        
        # 收集所有联系人的 user_id
        contact_ids = set()
        for contact in contacts:
            if contact.user_id == user_id:
                contact_ids.add(contact.contact_user_id)
            else:
                contact_ids.add(contact.user_id)
        
        # 筛选出在线的联系人
        online_contacts = [cid for cid in contact_ids if cid in self.active_connections]
        return online_contacts
    
    async def broadcast_to_contacts(self, user_id: int, message: dict, db):
        """向用户的所有联系人广播消息"""
        from app.models.contact import Contact
        
        # 获取该用户的所有联系人
        contacts = db.query(Contact).filter(
            (Contact.user_id == user_id) | (Contact.contact_user_id == user_id)
        ).all()
        
        # 收集所有联系人的 user_id
        contact_ids = set()
        for contact in contacts:
            if contact.user_id == user_id:
                contact_ids.add(contact.contact_user_id)
            else:
                contact_ids.add(contact.user_id)
        
        # 向在线的联系人发送消息
        for contact_id in contact_ids:
            if contact_id in self.active_connections:
                await self.send_personal_message(contact_id, message)
    
    async def broadcast_user_status(self, user_id: int, status: str, db):
        """广播用户在线状态给其联系人，并更新数据库
        
        Args:
            user_id: 用户ID
            status: 'online' 或 'offline'
            db: 数据库会话
        """
        from app.models.user import User
        from datetime import datetime, timedelta
        
        # 更新数据库中的用户状态
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.status = status
            if status == "offline":
                user.last_seen = datetime.utcnow() + timedelta(hours=8)
            else:
                user.last_seen = None
            db.commit()
            logger.info(f"用户 {user_id} 状态已更新为 {status}")
        
        # 广播状态变化给联系人
        message = {
            "type": f"user_{status}",
            "data": {"user_id": user_id}
        }
        await self.broadcast_to_contacts(user_id, message, db)
    
    async def cleanup_stale_connections(self):
        """清理失效的连接"""
        stale_users = []
        for user_id, websocket in self.active_connections.items():
            try:
                # 尝试发送 ping 检测连接状态
                await asyncio.wait_for(
                    websocket.send_text(json.dumps({"type": "ping"})),
                    timeout=1.0
                )
            except Exception:
                stale_users.append(user_id)
        
        for user_id in stale_users:
            self.disconnect(user_id)
            logger.info(f"清理失效连接: 用户 {user_id}")
    
    # ========== 语音通话相关方法 ==========
    
    async def send_binary_message(self, user_id: int, data: bytes):
        """发送二进制消息给指定用户（用于音频流）"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_bytes(data)
                return True
            except Exception as e:
                logger.error(f"发送二进制消息给用户 {user_id} 失败: {e}")
                return False
        return False
    
    def is_in_call(self, user_id: int) -> bool:
        """检查用户是否正在通话中"""
        return user_id in self.active_calls
    
    def start_call(self, caller_id: int, receiver_id: int):
        """建立通话映射"""
        self.active_calls[caller_id] = receiver_id
        self.active_calls[receiver_id] = caller_id
        logger.info(f"通话建立: {caller_id} <-> {receiver_id}")
    
    def end_call(self, user_id: int) -> int | None:
        """结束通话，返回对方的 user_id"""
        peer_id = self.active_calls.get(user_id)
        if peer_id:
            self.active_calls.pop(user_id, None)
            self.active_calls.pop(peer_id, None)
            logger.info(f"通话结束: {user_id} <-> {peer_id}")
        return peer_id
    
    def get_call_peer(self, user_id: int) -> int | None:
        """获取通话对方的 user_id"""
        return self.active_calls.get(user_id)


# 全局单例
manager = ConnectionManager()
