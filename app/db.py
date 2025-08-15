from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import SQLALCHEMY_DATABASE_URL, Base

# 创建数据库引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # SQLite需要这个参数
)

# 创建SessionLocal类用于数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
