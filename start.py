# start.py
import uvicorn
import os

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1,
        loop="asyncio",
        timeout_keep_alive=75,  # 增加到75秒，避免WebSocket频繁断开
        limit_concurrency=200,  # 增加并发限制
        limit_max_requests=5000,  # 增加最大请求数
        backlog=2048,  # 增加连接队列
        # ↓↓↓ 新增：本地 https，证书用 mkcert 生成的
        #如果不用本地开发就注释掉下面两行
        ssl_keyfile="localhost.key",   # 私钥
        ssl_certfile="localhost.crt",  # 证书
    )


"""
Windows 友好的 uvicorn 启动脚本
解决 WinError 10055 问题
目前后端的启动命令
python start.py
这个没有用https
"""
# import uvicorn

# if __name__ == "__main__":
#     # 在 Windows 上使用单进程模式
#     uvicorn.run(
#         "main:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=True,
#         # 关键：不使用多进程，避免 Windows 套接字问题
#         workers=1,
#         # 使用 asyncio 事件循环（Windows 兼容）
#         loop="asyncio",
#         # 减少连接超时
#         timeout_keep_alive=30,
#         # 限制并发连接数
#         limit_concurrency=100,
#         limit_max_requests=1000
#     )
