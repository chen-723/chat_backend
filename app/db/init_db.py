# 把模型先引进来，Base 才知道要建哪些表
from app.db.database import Base, engine
from app.models import user, contact, messages, groups, group_members, group_messages
import time
import logging

logger = logging.getLogger(__name__)

def init():
    """
    初始化数据库表
    使用重试机制处理并发DDL冲突
    """
    max_retries = 5
    retry_delay = 2  # 秒
    
    for attempt in range(max_retries):
        try:
            # 如果表已存在则跳过；有新字段会自动加
            Base.metadata.create_all(bind=engine, checkfirst=True)
            logger.info("✅ 数据库表已创建/更新完成")
            print("✅ 数据库表已创建/更新完成")
            return
        except Exception as e:
            error_msg = str(e)
            # 检查是否是并发DDL错误
            if "1684" in error_msg or "concurrent DDL" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(f"⚠️ 检测到并发DDL操作，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    print(f"⚠️ 检测到并发DDL操作，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ 数据库初始化失败，已达到最大重试次数: {error_msg}")
                    print(f"❌ 数据库初始化失败: {error_msg}")
                    raise
            else:
                # 其他错误直接抛出
                logger.error(f"❌ 数据库初始化失败: {error_msg}")
                print(f"❌ 数据库初始化失败: {error_msg}")
                raise

if __name__ == "__main__":
    init()