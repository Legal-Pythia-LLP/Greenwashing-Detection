from .db import init_db, engine
from .config import SQLALCHEMY_DATABASE_URL
from .models.report import ReportFile, Report  # Explicit model imports
import sqlite3

def migrate_db():
    """Check and automatically migrate database schema"""
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
        db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if reports table has analysis_summary_i18n
        cursor.execute("PRAGMA table_info(reports)")
        columns = [col[1] for col in cursor.fetchall()]
        if "analysis_summary_i18n" not in columns:
            cursor.execute("ALTER TABLE reports ADD COLUMN analysis_summary_i18n TEXT")
            print("✅ Auto migration: added reports.analysis_summary_i18n column")
        else:
            print("ℹ️ Column analysis_summary_i18n already exists, no migration needed")

        conn.commit()
        conn.close()


if __name__ == "__main__":
    print(f"Initializing database at {SQLALCHEMY_DATABASE_URL}")
    init_db()      # Ensure tables exist
    migrate_db()   # Auto migrate missing fields
    print("Database initialized successfully")
