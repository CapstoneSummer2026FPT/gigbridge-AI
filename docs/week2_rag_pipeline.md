# Week 2: Semantic Search & Custom RAG Pipeline

This guide outlines the custom RAG pipeline built in Week 2, which avoids dependency bloat by utilizing native Python logic and persistent Chroma DB collections.

## 1. Native Document Chunking
The `RAGService` chunks large documents (resumes, job requirements) using character/word boundaries:
*   `chunk_size`: Max words per chunk (default: 1000).
*   `chunk_overlap`: Word overlap to preserve context across boundaries (default: 200).

## 2. Embedding Generation
Chroma DB queries are matched against text vectors. We query OpenAI's `text-embedding-3-large` model:
*   Generates a 3072-dimension semantic vector representing the text meaning.

## 3. Persistent Store: Chroma DB
Vector storage uses `ChromaDBClient` wrapping a persistent database on disk (`CHROMA_DB_PATH`).
*   Stores candidate profiles under the `candidates` collection.
*   Supports fast cosine distance queries to retrieve top candidate documents (`top_k`).

## 4. LLM-Based Reranking
Standard vector search sorts matches by purely mathematical cosine distance, which can miss nuanced context. The RAG pipeline adds an LLM Reranking step:
1.  Retrieves top $N$ candidates (e.g. $N=15$).
2.  Passes candidates to the LLM Gateway along with the user's query.
3.  Instructs the LLM to sort the candidates by relevance and return a JSON list of sorted indices.
4.  Re-orders the candidates and slices the list to return the top $K$ results (e.g. $K=5$).
