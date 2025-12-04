# 把模型先引进来，Base 才知道要建哪些表
from app.db.database import Base, engine
from app.models import user, Contact          # 只要 import 一次即可注册

def init():
    # 如果表已存在则跳过；有新字段会自动加
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表已创建/更新完成")

if __name__ == "__main__":
    init()