# cleanup.py
import os
import time
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

STATIC_DIR = Path("static")          # 你的静态资源根目录
DAYS_KEEP  = 7                       # 几天前的文件视为过期
EXCLUDE_DIRS = ["avatars"]           # 排除的目录（用户/群头像不清理）

def remove_old_files():
    """同步清理函数，会被调度器周期执行"""
    now = time.time()
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
                        print(f"[cleanup] deleted {fpath}")
                    except Exception as e:
                        print(f"[cleanup] failed to delete {fpath}: {e}")

def start_scheduler(app: FastAPI):
    """把调度器挂到 FastAPI 生命周期"""
    scheduler = AsyncIOScheduler()
    # 每天凌晨 2:30 跑一次
    scheduler.add_job(remove_old_files, "cron", hour=2, minute=30)
    scheduler.start()

    @app.on_event("shutdown")
    async def shutdown_scheduler():
        scheduler.shutdown()