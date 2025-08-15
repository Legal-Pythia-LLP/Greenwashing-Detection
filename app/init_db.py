from .db import init_db
from .config import SQLALCHEMY_DATABASE_URL
from .models.report import ReportFile, Report  # 显式导入模型

if __name__ == "__main__":
    print(f"Initializing database at {SQLALCHEMY_DATABASE_URL}")
    init_db()
    print("Database initialized successfully")
