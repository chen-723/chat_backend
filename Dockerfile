# 使用官方 Python 3.11 镜像
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖描述，利用缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制源码
COPY . .

# 创建静态文件目录
RUN mkdir -p /app/static/avatars /app/static/uploads

# 容器内监听 8000
EXPOSE 8000

# 启动命令 - 使用单worker避免并发DDL冲突
# 如需多worker，请在docker-compose中设置SKIP_DB_INIT=1并单独运行初始化
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--loop", "asyncio", \
     "--timeout-keep-alive", "75", \
     "--limit-concurrency", "200", \
     "--limit-max-requests", "5000", \
     "--backlog", "2048"]