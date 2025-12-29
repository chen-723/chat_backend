from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.websocket.manager import manager
from app.core.security import verify_token
from app.db.database import SessionLocal
from jose import JWTError
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket连接端点
    
    Query参数:
        - token: JWT认证令牌
    """
    user_id = None
    db = None
    
    try:
        # 验证token
        payload = verify_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        # 为WebSocket创建独立的数据库会话
        db = SessionLocal()
        
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
                # 接收消息（可能是文本或二进制）
                message_data = await websocket.receive()
                
                # 处理二进制消息（音频流）
                if "bytes" in message_data:
                    audio_data = message_data["bytes"]
                    # 转发音频数据给通话对方
                    peer_id = manager.get_call_peer(user_id)
                    if peer_id:
                        await manager.send_binary_message(peer_id, audio_data)
                    continue
                
                # 处理文本消息（信令）
                if "text" in message_data:
                    data = message_data["text"]
                    try:
                        message = json.loads(data)
                        msg_type = message.get("type")
                        
                        # 心跳检测
                        if msg_type == "ping":
                            await websocket.send_text(json.dumps({
                                "type": "pong",
                                "data": {"timestamp": message.get("timestamp")}
                            }))
                        
                        # 语音通话请求
                        elif msg_type == "voice_call_request":
                            receiver_id = message.get("to_user_id")
                            caller_name = message.get("caller_name")
                            caller_avatar = message.get("caller_avatar")
                            
                            # 检查对方是否在线
                            if not manager.is_online(receiver_id):
                                await websocket.send_text(json.dumps({
                                    "type": "voice_call_failed",
                                    "data": {"reason": "对方不在线"}
                                }))
                                continue
                            
                            # 检查自己是否正在通话
                            if manager.is_in_call(user_id):
                                await websocket.send_text(json.dumps({
                                    "type": "voice_call_failed",
                                    "data": {"reason": "您正在通话中"}
                                }))
                                continue
                            
                            # 检查对方是否正在通话
                            if manager.is_in_call(receiver_id):
                                await websocket.send_text(json.dumps({
                                    "type": "voice_call_busy",
                                    "data": {"reason": "对方正在通话中"}
                                }))
                                continue
                            
                            # 转发通话请求给对方
                            await manager.send_personal_message(receiver_id, {
                                "type": "voice_call_incoming",
                                "data": {
                                    "caller_id": user_id,
                                    "caller_name": caller_name,
                                    "caller_avatar": caller_avatar
                                }
                            })
                        
                        # 接受通话
                        elif msg_type == "voice_call_accept":
                            caller_id = message.get("caller_id")
                            receiver_name = message.get("receiver_name")
                            receiver_avatar = message.get("receiver_avatar")
                            
                            # 检查发起方是否还在线
                            if not manager.is_online(caller_id):
                                await websocket.send_text(json.dumps({
                                    "type": "voice_call_failed",
                                    "data": {"reason": "对方已离线"}
                                }))
                                continue
                            
                            # 检查发起方是否已经在通话中（可能接了其他人的电话）
                            if manager.is_in_call(caller_id):
                                await websocket.send_text(json.dumps({
                                    "type": "voice_call_failed",
                                    "data": {"reason": "对方已在通话中"}
                                }))
                                continue
                            
                            # 建立通话映射
                            manager.start_call(caller_id, user_id)
                            
                            # 通知发起方通话已接通
                            await manager.send_personal_message(caller_id, {
                                "type": "voice_call_connected",
                                "data": {
                                    "peer_id": user_id,
                                    "peer_name": receiver_name,
                                    "peer_avatar": receiver_avatar
                                }
                            })
                            
                            # 通知接收方通话已接通
                            await websocket.send_text(json.dumps({
                                "type": "voice_call_connected",
                                "data": {
                                    "peer_id": caller_id
                                }
                            }))
                        
                        # 拒绝通话
                        elif msg_type == "voice_call_reject":
                            caller_id = message.get("caller_id")
                            
                            # 通知发起方被拒绝
                            await manager.send_personal_message(caller_id, {
                                "type": "voice_call_rejected",
                                "data": {"reason": "对方拒绝了通话"}
                            })
                        
                        # 取消通话（呼叫中主动挂断）
                        elif msg_type == "voice_call_cancel":
                            receiver_id = message.get("receiver_id")
                            
                            # 通知接收方通话已取消
                            if receiver_id:
                                await manager.send_personal_message(receiver_id, {
                                    "type": "voice_call_cancelled",
                                    "data": {"reason": "对方已取消通话"}
                                })
                        
                        # 挂断通话
                        elif msg_type == "voice_call_hangup":
                            peer_id = manager.end_call(user_id)
                            
                            if peer_id:
                                # 通知对方通话已结束
                                await manager.send_personal_message(peer_id, {
                                    "type": "voice_call_ended",
                                    "data": {"reason": "对方已挂断"}
                                })
                        
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
            # 如果用户正在通话中，通知对方挂断
            peer_id = manager.end_call(user_id)
            if peer_id:
                await manager.send_personal_message(peer_id, {
                    "type": "voice_call_ended",
                    "data": {"reason": "对方已断开连接"}
                })
            
            # 广播用户下线状态给其联系人
            if db:
                try:
                    await manager.broadcast_user_status(user_id, "offline", db)
                except Exception as e:
                    logger.error(f"广播下线状态失败: {e}")
            
            manager.disconnect(user_id)
            logger.info(f"清理用户 {user_id} 的连接资源")
        
        # 关闭数据库会话
        if db:
            try:
                db.close()
            except Exception as e:
                logger.error(f"关闭数据库会话失败: {e}")
