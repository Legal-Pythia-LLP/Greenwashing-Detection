import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy.ext.declarative import declarative_base

# SQLAlchemy Base class
Base = declarative_base()

# Environment variable loading
load_dotenv()

# Environment variables
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY_2 = os.getenv("AZURE_OPENAI_API_KEY_2")
AZURE_OPENAI_ENDPOINT_2 = os.getenv("AZURE_OPENAI_ENDPOINT_2")
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")
WIKIRATE_API_KEY = os.getenv("WIKIRATE_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


# Paths
BASE_PATH = Path(__file__).parent.parent  # Point to project root directory
UPLOAD_DIR = BASE_PATH / "uploads"   # Directory for saving uploaded files
REPORT_DIR = BASE_PATH / "reports"   # Directory for saving report files
DB_PATH = BASE_PATH / "data/reports.db"  # SQLite database path
COMPANIES_PATH = BASE_PATH / "data_files/companies.csv"    # Company whitelist CSV file path

# Ensure directories exist
REPORT_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Load valid companies
if COMPANIES_PATH.exists():
    df = pd.read_csv(COMPANIES_PATH)
    VALID_COMPANIES = [name.lower() for name in df["company_names"].to_list()]
else:
    VALID_COMPANIES = []

# Restrict upload file types (only allow PDF)
VALID_UPLOAD_TYPES = ["application/pdf"] 

# Database connection URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
