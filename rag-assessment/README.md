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
4. **Vector Store**: Indexes and stores chunks and embeddings in persistent ChromaDB, scoped by the browser session boundary.
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


## Upload and data boundaries

- Uploads accept PDF, DOCX, and PPTX files up to 10 MB. The backend validates both the extension and file signature/package structure.
- DOCX/PPTX archives are also bounded after decompression: at most 5000 entries, 25 MB per member, and 50 MB total expanded size (all configurable), blocking ZIP-bomb resource exhaustion.
- The original filename is sanitized for display. Files are written with random storage names and deleted after ingestion, preventing traversal and accidental overwrite.
- The browser sends an opaque `X-Session-ID`. Uploads, document lists, and retrieval are filtered to that session. This is an isolation boundary for the current unauthenticated app, not user authentication; a production multi-user deployment should replace it with an authenticated user or tenant ID.
- Client responses use safe error messages. Detailed exceptions remain in server logs.
