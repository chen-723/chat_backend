from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import auth, user, contact
from app.core.config import settings
import os

app = FastAPI(title="Chat Demo")

# 挂载静态文件目录
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/api/auth", tags=["User"])
app.include_router(contact.router, prefix="/api/contacts", tags=["Contacts"])

# 根路由
@app.get("/")
def root():
    return {"msg": "FastAPI 聊天服务已启动"}