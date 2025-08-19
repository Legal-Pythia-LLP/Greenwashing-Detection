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
    """Check and automatically migrate database schema (SQLite only)"""
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


def init_db():
    """Initialize database, create all tables and run migrations"""
    Base.metadata.create_all(bind=engine)  # Create tables (if not exist)
    migrate_db()  # Auto migrate missing fields


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
