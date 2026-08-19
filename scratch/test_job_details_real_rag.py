import asyncio
import sys
import os

# Adjust path to import app modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.job_posts import JobPostGenerationRequest
from app.services.job_posts import get_job_post_service

async def test_generation():
    service = get_job_post_service()
    
    request = JobPostGenerationRequest(
        client_prompt="Looking for a Python/FastAPI backend developer to build a secure document management system using PostgreSQL, Docker, and FastAPI. Needs to support document upload, vector search (RAG) with source tracking, and scalability."
    )
    
    print("Sending details generation request to AI Job Post Service with REAL RAG (Precision style)...")
    response = await service.generate_job_details(request)
    print("\n--- GENERATED DETAILS RESPONSE ---")
    print(f"Title: {response.title}")
    print(f"Major ID: {response.major_id}")
    print(f"Category ID: {response.category_id}")
    print(f"System Skill IDs: {response.system_skill_ids}")
    print(f"Custom Skills: {response.custom_skills}")
    print(f"Budget Min: {response.budget_min}")
    print(f"Budget Max: {response.budget_max}")
    print(f"Estimated Duration: {response.estimated_duration}")
    print("\n--- GENERATED DESCRIPTION ---\n")
    print(response.description)
    print("\n-----------------------------\n")
    print(f"Is AI Generated: {response.is_ai_generated}")

if __name__ == "__main__":
    asyncio.run(test_generation())
