from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import auth, user, contact, messages, groups
from app.websocket import router as websocket_router
from app.core.config import settings
import os


from app.db.init_db import init

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ===== 启动阶段 =====
    init()   # 建库 / 建表
    yield
    # ===== 关闭阶段 =====
    pass

app = FastAPI(
    title="Chat Demo",
    lifespan=lifespan
)


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