import asyncio
import sys
import os

# Adjust path to import app modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.rag import AnswerConfig, RetrievalGroup
from app.services.rag import get_rag_service

async def test_retrieval():
    rag = get_rag_service()
    
    question = "Looking for a Python/FastAPI backend developer to build a secure document management system using PostgreSQL, Docker, and FastAPI. Needs to support document upload, vector search (RAG) with source tracking, and scalability."
    
    config = AnswerConfig(
        style="precision",
        collection_name="ai-create-job-post",
        retrieval_groups=[
            RetrievalGroup(name="majors", n_results=10, where={"type": "major"}),
            RetrievalGroup(name="categories", n_results=15, where={"type": "category"}),
            RetrievalGroup(name="skills", n_results=15, where={"type": "skill"}),
        ]
    )
    
    result = await rag.answer_question(question, config)
    
    print("\n--- RETRIEVED SOURCES BY GROUP ---")
    majors = []
    categories = []
    skills = []
    
    for src in result.sources:
        meta = src.get("metadata", {})
        item_type = meta.get("type")
        item_id = meta.get("major_id") or meta.get("category_id") or meta.get("skill_id")
        item_name = meta.get("name")
        page_content = src.get("page_content")
        
        info = f"ID: {item_id} | Name: {item_name} | Text: {page_content.splitlines()[0] if page_content else ''}"
        if item_type == "major":
            majors.append(info)
        elif item_type == "category":
            categories.append(info)
        elif item_type == "skill":
            skills.append(info)
            
    print("\n[MAJORS]")
    for m in majors:
        print(f"  - {m}")
        
    print("\n[CATEGORIES]")
    for c in categories:
        print(f"  - {c}")
        
    print("\n[SKILLS]")
    for s in skills:
        print(f"  - {s}")
        
if __name__ == "__main__":
    asyncio.run(test_retrieval())
