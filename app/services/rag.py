import uuid
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.clients.db.chroma import ChromaDBClient, get_chroma_client
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.core.config import settings
from app.core.exceptions import RAGException

logger = logging.getLogger("ai_server.rag_service")

class RAGService:
    """Service coordinates custom RAG pipelines (indexing, embeddings, retrieval, and reranking)"""
    
    def __init__(
        self,
        chroma_client: ChromaDBClient = get_chroma_client(),
        llm_gateway: LLMGateway = get_llm_gateway()
    ):
        self.chroma = chroma_client
        self.llm = llm_gateway
        self.embedding_model = settings.EMBEDDING_MODEL
        # Initialize AsyncOpenAI only for embeddings
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    def chunk_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """
        Splits text into overlapping chunks.
        """
        words = text.split()
        chunks = []
        # Calculate stride
        stride = chunk_size - chunk_overlap
        if stride <= 0:
            stride = chunk_size // 2
            
        for i in range(0, len(words), stride):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))
            if i + chunk_size >= len(words):
                break
        return chunks

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate vector embeddings for input texts using OpenAI client.
        """
        if not self.openai_client:
            raise RAGException("OpenAI API Key is not configured for generating embeddings.")
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            return [e.embedding for e in response.data]
        except Exception as e:
            raise RAGException(f"Failed to generate embeddings: {str(e)}")

    async def add_documents(self, collection_name: str, text: str, metadata: Dict[str, Any]) -> None:
        """
        Chunks text, embeds it, and writes chunks to Chroma DB collection.
        """
        chunks = self.chunk_text(text)
        if not chunks:
            return
            
        embeddings = await self.get_embeddings(chunks)
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [metadata.copy() for _ in chunks]
        
        try:
            self.chroma.add_documents(
                collection_name=collection_name,
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas
            )
        except Exception as e:
            raise RAGException(f"Failed to write documents to vector DB: {str(e)}")

    async def retrieve_context(self, collection_name: str, query: str, top_k: int = 15) -> List[Dict[str, Any]]:
        """
        Embeds query, searches Chroma DB, and returns candidate documents.
        """
        try:
            query_vector = (await self.get_embeddings([query]))[0]
            results = self.chroma.query_documents(
                collection_name=collection_name,
                query_embeddings=[query_vector],
                n_results=top_k
            )
            
            docs = []
            if results and results["documents"]:
                for i in range(len(results["documents"][0])):
                    docs.append({
                        "id": results["ids"][0][i],
                        "page_content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                    })
            return docs
        except Exception as e:
            raise RAGException(f"Context retrieval failed: {str(e)}")

    async def rerank(self, query: str, candidates: List[Dict[str, Any]], final_k: int = 5) -> List[Dict[str, Any]]:
        """
        Uses LLM as a re-ranker to order candidate documents by relevance to query.
        """
        if not candidates:
            return []
            
        system_prompt = (
            "You are a document re-ranker.\n"
            "You are provided with a search query and a list of text extracts.\n"
            "Rank the extracts by relevance to the query, listing the most relevant first.\n"
            "Respond ONLY with a JSON object in this format:\n"
            '{"ranked_indices": [2, 0, 1]}\n'
            "where values are 0-based indices matching the input list sequence. Include all indices."
        )
        
        user_prompt = f"Query: {query}\n\nList of candidate extracts:\n"
        for idx, doc in enumerate(candidates):
            user_prompt += f"Extract Index {idx}:\n{doc['page_content']}\n\n"
            
        try:
            # Import a Pydantic structure for parsing
            from pydantic import BaseModel, Field
            class RerankResult(BaseModel):
                ranked_indices: List[int] = Field(description="Order of 0-based candidate indices by relevance")
            
            logger.info("Executing LLM-based reranking")
            response = await self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format=RerankResult
            )
            
            import json
            data = json.loads(response)
            order = data.get("ranked_indices", [])
            
            # Sort candidates according to list order and slice
            reranked = [candidates[i] for i in order if i < len(candidates)]
            return reranked[:final_k]
        except Exception as e:
            logger.warning(f"Reranking failed: {str(e)}. Defaulting to vector distance ordering.")
            # Fallback to standard Chroma DB cosine distance ordering
            return candidates[:final_k]

# Dependency helper
_rag_service = RAGService()

def get_rag_service() -> RAGService:
    return _rag_service
