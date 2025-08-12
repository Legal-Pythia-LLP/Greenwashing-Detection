import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

# 环境变量加载
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
BASE_PATH = Path(__file__).parent.parent  # 指向项目根目录
UPLOAD_DIR = BASE_PATH / "uploads"   # 上传文件保存目录
COMPANIES_PATH = BASE_PATH / "data_files/companies.csv"    # 公司白名单 CSV 文件路径

# Load valid companies
if COMPANIES_PATH.exists():
    df = pd.read_csv(COMPANIES_PATH)
    VALID_COMPANIES = [name.lower() for name in df["company_names"].to_list()]
else:
    VALID_COMPANIES = []

# 限制上传文件类型（只允许 PDF）
VALID_UPLOAD_TYPES = ["application/pdf"] 