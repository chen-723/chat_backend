from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session
from app.websocket.manager import manager
from app.core.security import verify_token
from app.db.database import get_db
from jose import JWTError
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    WebSocket连接端点
    
    Query参数:
        - token: JWT认证令牌
    """
    user_id = None
    
    try:
        # 验证token
        payload = verify_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        # 建立连接
        await manager.connect(user_id, websocket)
        
        # 获取在线联系人列表并发送给当前用户
        online_contacts = await manager.get_online_contacts(user_id, db)
        await websocket.send_text(json.dumps({
            "type": "online_users",
            "data": {"user_ids": online_contacts}
        }, ensure_ascii=False))
        
        # 广播用户上线状态给其联系人
        await manager.broadcast_user_status(user_id, "online", db)
        
        # 发送连接成功消息
        await websocket.send_text(json.dumps({
            "type": "connected",
            "data": {"user_id": user_id, "message": "连接成功"}
        }, ensure_ascii=False))
        
        # 保持连接，监听客户端消息
        while True:
            try:
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    msg_type = message.get("type")
                    
                    # 心跳检测
                    if msg_type == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "data": {"timestamp": message.get("timestamp")}
                        }))
                    
                    # 可以在这里处理其他类型的客户端消息
                    
                except json.JSONDecodeError:
                    logger.warning(f"收到无效JSON: {data}")
            
            except WebSocketDisconnect:
                logger.info(f"用户 {user_id} 主动断开连接")
                break
            except Exception as e:
                logger.error(f"接收消息时出错: {e}")
                break
                
    except JWTError:
        try:
            await websocket.close(code=1008, reason="Token验证失败")
        except Exception:
            pass
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
    finally:
        if user_id:
            # 广播用户下线状态给其联系人
            await manager.broadcast_user_status(user_id, "offline", db)
            manager.disconnect(user_id)
            logger.info(f"清理用户 {user_id} 的连接资源")
