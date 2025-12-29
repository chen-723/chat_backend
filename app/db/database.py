from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import settings

# 配置数据库连接池，防止连接耗尽和超时
engine = create_engine(
    settings.DATABASE_URI,
    echo=False,  # 生产环境关闭SQL日志，减少IO
    poolclass=QueuePool,
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 超出pool_size后最多再创建的连接数
    pool_timeout=30,  # 获取连接的超时时间（秒）
    pool_recycle=3600,  # 1小时回收连接，防止MySQL超时断开
    pool_pre_ping=True,  # 每次从池中取连接前先ping，确保连接有效
    connect_args={
        "connect_timeout": 10,  # 连接超时
        "read_timeout": 30,  # 读取超时
        "write_timeout": 30,  # 写入超时
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()