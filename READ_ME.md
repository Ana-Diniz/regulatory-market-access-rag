# Regulatory Market Access RAG Pipeline 🏥📊

An AI Deployment and Data Engineering prototype designed to transform unstructured regulatory health technology assessment reports (e.g., CONITEC PDFs) into a structured, queryable, and traceable institutional memory.

## 🎯 Problem Statement

In Market Access, regulatory decisions are buried inside hundreds of dense, unstructured PDF pages. Traditional summaries do not create comparable data. This project solves the decentralization of evidence by implementing an extractive RAG (Retrieval-Augmented Generation) pipeline. It reads the document, retrieves semantic matches, and forces the extraction into a strict JSON schema, preserving the exact source page for auditability.

## 🚀 Architecture & Tech Stack

- **Data Ingestion:** `PyMuPDF` and `langchain-text-splitters` for layout-aware parsing and semantic chunking.
- **Embeddings & Vector DB:** `sentence-transformers` (`all-MiniLM-L6-v2`) operating 100% locally with `ChromaDB`, enforcing a Private Cloud architecture to prevent data leaks.
- **Orchestration & LLM:** `LangChain` routing context to `Groq` API (Qwen 2.5).
- **Data Modeling:** Strict enforcement of entity schemas using `Pydantic` to eliminate hallucinations and generate structured outputs.

## 🟢 Current Status (Phase 1 Completed)

The core pipeline is fully functional with isolated data ingestion and structured extraction.

- **Traceability:** Successfully implemented metadata injection during chunking to trace every extracted data point back to its original PDF page.
- **Private Vector Search:** Local ChromaDB instance is successfully building and querying vector embeddings.
- **Advanced RAG Optimization:** Diagnosed and resolved "Context Poisoning" and LLM hallucination issues by decoupling the _Retrieval Query_ (optimized for keyword matching on the Executive Summary) from the _System Prompt_ (optimized for strict Pydantic schema enforcement).

## 🟡 Roadmap (Phase 2 & 3)

- [ ] **Relational Persistence:** Implement SQLite to store the validated JSON extractions, creating a factual database.
- [ ] **Human-in-the-Loop UI:** Build a Streamlit application to allow human auditing and correction of the extracted data before database insertion.
- [ ] **Analytics Dashboard:** Generate visualizations directly from the SQLite relational database for Market Access intelligence.

## ⚙️ How to Run

1. Clone this repository.
2. Create and activate an isolated virtual environment (`python -m venv venv`).
3. Install dependencies: `pip install -r requirements.txt`.
4. Create a `.env` file and add your `GROQ_API_KEY`.
5. Place target PDFs inside the `data/` directory.
6. Run `python build_db.py` to populate the local vector database.
7. Run `python extract.py` to perform the structured query.
