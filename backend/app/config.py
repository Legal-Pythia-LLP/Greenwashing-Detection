import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from app.models.base import Base
from app.models import ESGAnalysisResult, ESGAnalysisState, ChatBaseMessage, ChatMessage, Conversation

# Load environment variables
load_dotenv()

# Environment variables
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")
WIKIRATE_API_KEY = os.getenv("WIKIRATE_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


# Paths
BASE_PATH = Path(__file__).parent.parent  # Points to project root
REPORT_DIR = BASE_PATH / "data/reports"   # Directory for report files
DB_PATH = BASE_PATH / "data/reports.db"  # SQLite database path
COMPANIES_PATH = BASE_PATH / "data/raw/companies.csv"    # Company whitelist CSV file path
WIKIRATE_COMPANIES_PATH = BASE_PATH / "data/raw/wikirate_companies_all.csv"    # Company whitelist CSV file path
VECTOR_STORE_DIR = BASE_PATH / "data/vector_stores"  # Directory for vector store persistence
DOWNLOADS_PATH = BASE_PATH / "data/downloads"

# Ensure directories exist
REPORT_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

# Load valid companies
if COMPANIES_PATH.exists():
    df = pd.read_csv(COMPANIES_PATH)
    VALID_COMPANIES = [name.lower() for name in df["company_names"].to_list()]
else:
    VALID_COMPANIES = []

# Restrict upload file types (PDF only)
VALID_UPLOAD_TYPES = ["application/pdf"] 

# Database connection URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
