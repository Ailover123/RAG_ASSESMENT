# RAG Assessment System

A full-stack Retrieval-Augmented Generation (RAG) system built with FastAPI, React (Vite), ChromaDB, Sentence-Transformers, and Groq LLM.

## Architecture Overview

```
rag-assessment/
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── chunking/         # Text splitting & semantic chunking
│   │   ├── embeddings/       # Sentence-transformers embedding wrapper
│   │   ├── ingestion/        # Document adapters (PDF, DOCX, PPTX) & router
│   │   ├── llm/              # Groq API client & prompt engineering
│   │   ├── routers/          # API endpoints (/upload, /query, /documents)
│   │   ├── vectorstore/      # ChromaDB client & vector search
│   │   ├── config.py         # Application settings & environment variables
│   │   └── main.py           # FastAPI entrypoint & CORS setup
│   ├── data/                 # Raw uploads and ChromaDB persistent storage
│   ├── .env.example          # Environment variables template
│   └── requirements.txt      # Python dependencies
├── frontend/                 # React + Vite Frontend
│   ├── src/
│   │   ├── components/       # UI Components (Uploader, DocList, ChatBox)
│   │   ├── api.js            # API client wrapper
│   │   ├── App.jsx           # Main application view
│   │   └── main.jsx          # React DOM entrypoint
│   └── package.json          # Node dependencies & Vite scripts
└── README.md
```

## System Flow

1. **Document Ingestion**: Multi-format document parser (PDF, DOCX, PPTX) extracts normalized `Document` objects.
2. **Chunking**: Splits extracted document text using recursive/semantic chunking strategies with configurable overlap.
3. **Embedding**: Generates dense vector representations using `sentence-transformers`.
4. **Vector Store**: Indexes and stores chunks and embeddings into persistent ChromaDB.
5. **Retrieval & LLM Generation**: Queries ChromaDB for top-k matching contexts, injects them into structured prompts, and streams responses via Groq.

---

## Setup & Getting Started

### 1. Backend Setup (FastAPI)

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and supply your GROQ_API_KEY

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

Backend API documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs).

### 2. Frontend Setup (React + Vite)

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

Frontend application will be accessible at [http://localhost:5173](http://localhost:5173).
