# cleanup.py
import os
import time
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)

STATIC_DIR = Path("static")          # 你的静态资源根目录
DAYS_KEEP  = 7                       # 几天前的文件视为过期
EXCLUDE_DIRS = ["avatars"]           # 排除的目录（用户/群头像不清理）

# 创建线程池执行器，避免阻塞事件循环
executor = ThreadPoolExecutor(max_workers=2)

def remove_old_files_sync():
    """同步清理函数，在独立线程中执行"""
    now = time.time()
    deleted_count = 0
    
    try:
        for root, _, files in os.walk(STATIC_DIR):
            # 跳过排除的目录
            root_path = Path(root)
            if any(excluded in root_path.parts for excluded in EXCLUDE_DIRS):
                continue
                
            for fname in files:
                fpath = Path(root) / fname
                if fpath.is_file():
                    # 跳过 .gitkeep / .gitignore 之类
                    if fname.startswith("."):
                        continue
                    mtime = fpath.stat().st_mtime
                    if now - mtime > DAYS_KEEP * 86400:
                        try:
                            fpath.unlink()
                            deleted_count += 1
                            logger.info(f"[cleanup] deleted {fpath}")
                        except Exception as e:
                            logger.error(f"[cleanup] failed to delete {fpath}: {e}")
        
        logger.info(f"[cleanup] 清理完成，删除了 {deleted_count} 个文件")
    except Exception as e:
        logger.error(f"[cleanup] 清理任务出错: {e}")

async def remove_old_files():
    """异步包装器，在线程池中执行同步清理"""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, remove_old_files_sync)

def start_scheduler(app: FastAPI):
    """把调度器挂到 FastAPI 生命周期"""
    scheduler = AsyncIOScheduler()
    # 每天凌晨 2:30 跑一次
    scheduler.add_job(remove_old_files, "cron", hour=2, minute=30)
    scheduler.start()
    logger.info("[cleanup] 定时清理任务已启动")

    @app.on_event("shutdown")
    async def shutdown_scheduler():
        scheduler.shutdown()
        executor.shutdown(wait=False)
        logger.info("[cleanup] 定时清理任务已关闭")