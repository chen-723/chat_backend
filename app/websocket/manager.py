from typing import Dict
from fastapi import WebSocket
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃连接: {user_id: WebSocket}
        self.active_connections: Dict[int, WebSocket] = {}
    
    async def connect(self, user_id: int, websocket: WebSocket):
        """建立连接"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"用户 {user_id} 已连接，当前在线: {len(self.active_connections)}")
    
    def disconnect(self, user_id: int):
        """断开连接"""
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


# 全局单例
manager = ConnectionManager()
