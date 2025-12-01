from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth
from app.core.config import settings

app = FastAPI(title="Chat Demo")

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

# 根路由
@app.get("/")
def root():
    return {"msg": "FastAPI 聊天服务已启动"}