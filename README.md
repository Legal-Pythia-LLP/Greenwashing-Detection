# ESG Greenwashing Analysis API

This project is based on FastAPI, LangChain, OpenAI/ClimateBERT, etc., providing an automated API for ESG greenwashing analysis. It has achieved complete modularization with clear structure, making it easy to maintain and extend.

## Tech Stack
- Backend: FastAPI, Uvicorn  
- AI: OpenAI, ClimateBERT, LangChain, LangGraph  
- Database: SQLite (built-in), FAISS (vector storage)  
- Frontend: React (under v2 directory)  
- Tools: Pydantic, BeautifulSoup (web scraping)  

## Main Features
- ESG report upload and automated analysis (PDF supported)  
- LangGraph workflow and Agent intelligent reasoning  
- News verification and greenwashing metrics quantification  
- Multi-model and custom tool extensions  
- Fully layered architecture design  

## Quick Start

### Environment Setup
Recommended Python 3.10+

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Database Initialization
```bash
python -m app.init_db
```

### Start Service
```bash
# Development mode
uvicorn app.main:app --reload

# Production mode
python -m app.main
```

## Project Structure

```
summer-pro/
├── app/                  # Backend core code
│   ├── api/              # API routes
│   ├── core/             # Business logic & tools
│   ├── models/           # Data models
│   ├── config.py         # Configuration management
│   └── main.py           # Application entry
├── v2/                   # Frontend React app
├── data/                 # Database files
├── pdfs/                 # Example ESG reports
├── uploads/              # Uploaded file storage
├── tests/                # Unit tests
└── webscraper/           # News scraper
```

