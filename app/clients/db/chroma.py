import os
import chromadb
from typing import List, Dict, Any, Optional
from app.core.config import settings

class ChromaDBClient:
    """Wrapper client for persistent Chroma DB vector database"""
    
    def __init__(self):
        self.db_path = settings.CHROMA_DB_PATH
        # Ensure path directory exists
        os.makedirs(self.db_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.db_path)

    def get_or_create_collection(self, name: str):
        return self.client.get_or_create_collection(name=name)

    def add_documents(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        collection = self.get_or_create_collection(collection_name)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metas if (metas := metadatas) else None
        )

    def query_documents(
        self,
        collection_name: str,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        collection = self.get_or_create_collection(collection_name)
        return collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where
        )

    def delete_collection(self, collection_name: str) -> None:
        try:
            self.client.delete_collection(name=collection_name)
        except Exception:
            pass

# Dependency injection helper
_chroma_client = ChromaDBClient()

def get_chroma_client() -> ChromaDBClient:
    return _chroma_client
