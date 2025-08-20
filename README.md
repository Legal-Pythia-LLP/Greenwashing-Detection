# Greenwashing-Detection

A comprehensive ESG (Environmental, Social, and Governance) greenwashing detection platform that combines a modern React frontend with a powerful FastAPI backend to analyze corporate sustainability reports and detect potential greenwashing practices.

## 🎯 Overview

Greenwashing-Detection is an AI-powered platform designed to help investors, analysts, and stakeholders identify and analyze potential greenwashing in corporate ESG reports. The system uses advanced natural language processing, machine learning, and data analytics to provide insights into the authenticity and credibility of sustainability claims.

## 🏗️ Architecture

The project consists of two main components:

### Backend (FastAPI)
- **Framework**: FastAPI with Python 3.11+
- **Features**: Document processing, AI chat, ESG analysis, vector storage, API integrations
- **Key Technologies**: Llama Cloud, WikiRate API, Google AI, OCR services

### Frontend (React + TypeScript)
- **Framework**: React 18 with TypeScript and Vite
- **Features**: Modern UI, multilingual support, data visualization, responsive design
- **Key Technologies**: Tailwind CSS, shadcn/ui, i18next, Recharts

## 🚀 Key Features

### Core Capabilities
- 📄 **Document Processing**: Upload and analyze PDF, HTML, and other document formats
- 💬 **AI Chat System**: Interactive conversation with ESG analysis capabilities
- 🔍 **Greenwashing Detection**: Advanced algorithms to identify misleading sustainability claims
- 📊 **Data Visualization**: Interactive dashboards and comprehensive reporting
- 🌐 **Multi-language Support**: English, Italian, German language interfaces

### Advanced Analytics
- Semantic search and vector storage for document analysis
- Integration with WikiRate for company data and ESG metrics
- Custom ESG scoring and risk assessment algorithms
- Comparative analysis across companies and industries

## 📋 Prerequisites

### Backend Requirements
- Python 3.11+
- uv (recommended) or pip
- Optional API keys for enhanced functionality

### Frontend Requirements
- Node.js 18+
- npm, yarn, or bun
- Modern web browser

## 🛠️ Installation & Setup

### Backend Setup
```bash
cd backend

# Using uv (recommended)
uv sync

# Or using traditional virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Frontend Setup
```bash
cd frontend/v2

# Install dependencies
npm install

# Start development server
npm run dev
```

## 🚀 Running the Application

### Start Backend
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend
```bash
cd frontend/v2
npm run dev
```

The application will be available at:
- Frontend: http://localhost:8080
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 📁 Project Structure

```
Greenwashing-Detection/
├── backend/                 # FastAPI backend application
│   ├── app/                # Main application code
│   ├── data/               # Data files and storage
│   ├── downloads/          # Downloaded content storage
│   └── pyproject.toml      # Python project configuration
├── frontend/v2/            # React frontend application
│   ├── src/                # Source code
│   ├── public/             # Static assets
│   └── package.json        # Node.js project configuration
└── pdf/                    # Sample ESG reports for testing
```

## 🔧 Development

### Backend Development
- Uses uv for fast dependency management
- Follows FastAPI best practices with proper type hints
- Includes comprehensive API documentation (Swagger/ReDoc)
- Modular architecture with clear separation of concerns

### Frontend Development
- Built with React 18 and TypeScript for type safety
- Uses Vite for fast development and building
- Implements modern UI patterns with shadcn/ui components
- Includes internationalization support