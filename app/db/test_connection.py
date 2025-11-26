# 测试文件，直接 python app/db/test_connection.py 运行
from sqlalchemy import text
from app.db.database import engine  # 拿刚才写好的引擎

def test():
    try:
        # 原生 SQL，随便执行一句
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ 数据库连接成功")
    except Exception as e:
        print("❌ 数据库连接失败：", e)

if __name__ == "__main__":
    test()