# ESG Greenwashing Analysis Backend

This is a FastAPI-based backend API service for ESG (Environmental, Social, and Governance) greenwashing analysis. The project provides features such as document upload, chat interaction, ESG report analysis, and data visualization.

## 🚀 Features

* 📄 Document upload and parsing (PDF, HTML, etc.)
* 💬 AI chat system
* 📊 ESG report analysis and greenwashing detection
* 🌐 WikiRate API integration
* 🔍 Vector storage and semantic search
* 📈 Data visualization and dashboards

## 📋 Prerequisites

* Python 3.11+
* uv (recommended) or pip
* Optional API keys (Google AI, Llama Cloud, WikiRate)

## 🛠️ Installation and Setup

### Method 1: Using uv (Recommended)

uv is a fast Python package manager and parser developed by Astral, faster and more reliable than pip.

1. **Install uv** (if not already installed):

```bash
# On Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Configure PATH environment variable** (if needed):
   After installation, the uv executable is usually located at:

* Windows: `C:\Users\<username>\.cargo\bin\uv.exe`
* macOS/Linux: `~/.local/bin/uv`

**Windows permanent PATH configuration**:

```powershell
# Permanently add uv to PATH (replace <username> with actual username)
setx PATH "$($env:PATH);$HOME\.cargo\bin"

# Restart terminal to apply changes
```

**macOS/Linux configuration**:
Add the following line to `~/.bashrc` or `~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then run: `source ~/.bashrc` or `source ~/.zshrc`

3. **Verify installation**:

```bash
uv --version
```

4. **Create virtual environment and install dependencies**:

```bash
cd backend

# Automatically create virtual environment and install dependencies
uv sync
```

5. **Activate virtual environment**:

```bash
# On Windows
.\.venv\Scripts\activate

# On Linux/macOS
source .venv/bin/activate
```

**Note**: Although `uv sync` automatically creates a virtual environment, you still need to activate it manually to use it in the current terminal session.

### Method 2: Using Traditional Virtual Environment

1. **Create virtual environment**:

```bash
cd backend

# Using venv module
python -m venv .venv
```

2. **Activate virtual environment**:

```bash
# On Windows
.\.venv\Scripts\activate

# On Linux/macOS
source .venv/bin/activate
```

3. **Install dependencies**:

```bash
# Using pip
pip install -r requirements.txt

# Or install from pyproject.toml
pip install -e .
```

### Activating requirements.txt

Regardless of the method, after installing dependencies, all packages in requirements.txt will be installed correctly. The project uses pyproject.toml as the main dependency management file.

## ⚙️ Environment Configuration

Edit the `.env` file and set the following optional API keys:

* `LLAMA_CLOUD_API_KEY` - Llama Cloud API key
* `WIKIRATE_API_KEY` - WikiRate API key
* `GOOGLE_API_KEY` - Google AI API key

## 🚀 Running the Application

### Development Mode

```bash
# Ensure virtual environment is activated
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The app will start at [http://localhost:8000](http://localhost:8000)

## 📁 Project Directory Structure

```
backend/
├── app/                          # Main application directory
│   ├── api/                      # API routes
│   │   ├── __init__.py
│   │   ├── chat.py               # Chat API
│   │   ├── dashboard.py          # Dashboard API
│   │   ├── language.py           # Language processing API
│   │   ├── report.py             # Report API
│   │   ├── upload.py             # File upload API
│   │   └── wikirateAPItest.py    # WikiRate API test
│   ├── core/                     # Core modules
│   │   ├── __init__.py
│   │   ├── company.py            # Company data processing
│   │   ├── document.py           # Document processing
│   │   ├── esg_analysis.py       # ESG analysis
│   │   ├── llm.py                # Large language model integration
│   │   ├── ocr_service.py        # OCR service
│   │   ├── store.py              # Data storage
│   │   ├── tools.py              # Utility functions
│   │   ├── utils.py              # Utility functions
│   │   ├── vector_store.py       # Vector storage
│   │   ├── workflow_validator.py # Workflow validation
│   │   └── webscraper/           # Web scrapers
│   │       ├── __init__.py
│   │       ├── bbc_search.py     # BBC search
│   │       └── cnn_search.py     # CNN search
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   ├── base.py               # Base models
│   │   ├── chat.py               # Chat models
│   │   ├── esg.py                # ESG models
│   │   └── report.py             # Report models
│   ├── config.py                 # Configuration management
│   ├── db.py                     # Database connection
│   ├── init_db.py                # Database initialization
│   └── main.py                   # Main application entry
├── data/                          # Data files
│   ├── raw/                       # Raw data
│   │   ├── companies.csv          # Company data
│   │   ├── rules.json             # Rules file
│   │   └── wikirate_*.csv         # WikiRate company data
│   ├── reports/                   # Report files
│   └── vector_stores/             # Vector storage data
├── downloads/                     # Download storage
├── main.py                        # Legacy entry file
├── pyproject.toml                 # Project configuration and dependencies
├── requirements.txt               # Dependency list
├── uv.lock                        # uv lock file
└── README.md                      # Project description
```

## 📚 API Documentation

After starting the app, access the API documentation at:

* Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
* ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 🔧 Development Guide

### Adding New Dependencies

Using uv to add a package:

```bash
uv add package-name
```

Using pip to add a package:

```bash
pip install package-name
```

Then update requirements.txt:

```bash
pip freeze > requirements.txt
```
