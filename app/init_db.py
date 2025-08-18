from .db import init_db, engine
from .config import SQLALCHEMY_DATABASE_URL
from .models.report import ReportFile, Report  # Explicit model imports
import sqlite3

def migrate_db():
    """检查并自动迁移数据库 schema"""
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


if __name__ == "__main__":
    print(f"Initializing database at {SQLALCHEMY_DATABASE_URL}")
    init_db()      # 确保表存在
    migrate_db()   # 自动迁移缺失字段
    print("Database initialized successfully")
