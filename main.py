from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import auth, user, contact, messages, groups
from app.websocket import router as websocket_router
from app.websocket.manager import manager
from app.core.config import settings
import os
import cleanup

from app.db.init_db import init

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== 启动阶段 =====
    # 只在主进程中初始化数据库，避免多worker并发DDL冲突
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    # 使用环境变量标记，确保只有一个进程执行初始化
    if os.environ.get("SKIP_DB_INIT") != "1":
        try:
            init()   # 建库 / 建表
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            # 不阻止应用启动，因为表可能已经被其他worker创建
    
    yield
    # ===== 关闭阶段 =====
    pass

app = FastAPI(
    title="Chat Demo",
    lifespan=lifespan
)
cleanup.start_scheduler(app)


# 挂载静态文件目录
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,  
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/api/auth", tags=["User"])
app.include_router(contact.router, prefix="/api/contacts", tags=["Contacts"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(groups.router, prefix="/api/groups", tags=["Groups"])
app.include_router(websocket_router.router, tags=["WebSocket"])

# 根路由
@app.get("/")
def root():
    return {"msg": "FastAPI 聊天服务已启动"}


@app.get("/health")
def health_check():
    """健康检查端点，用于监控服务状态"""
    from app.db.database import engine
    try:
        # 测试数据库连接
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "websocket_connections": len(manager.active_connections)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }