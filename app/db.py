from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import SQLALCHEMY_DATABASE_URL, Base
import sqlite3

# Create database engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Required for SQLite
)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def migrate_db():
    """检查并自动迁移数据库 schema（仅 SQLite 用）"""
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
        db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查 reports 表是否有 analysis_summary_i18n
        cursor.execute("PRAGMA table_info(reports)")
        columns = [col[1] for col in cursor.fetchall()]
        if "analysis_summary_i18n" not in columns:
            cursor.execute("ALTER TABLE reports ADD COLUMN analysis_summary_i18n TEXT")
            print("✅ 自动迁移: 已添加 reports.analysis_summary_i18n 字段")
        else:
            print("ℹ️ 字段 analysis_summary_i18n 已存在，无需迁移")

        conn.commit()
        conn.close()


def init_db():
    """Initialize database, create all tables and run migrations"""
    Base.metadata.create_all(bind=engine)  # 创建表（如果不存在）
    migrate_db()  # 自动迁移缺失字段


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
