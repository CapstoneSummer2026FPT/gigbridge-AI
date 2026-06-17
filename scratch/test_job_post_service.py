import asyncio
import sys
import os

# Adjust path to import app modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.schemas.job_posts import JobPostGenerationRequest
from app.services.job_posts import get_job_post_service

async def test_generation():
    service = get_job_post_service()
    
    # Define a request payload with major, category, and skills options
    # Note: RAG/AI-related skills are intentionally excluded from available_skills
    request = JobPostGenerationRequest(
        title="Build an AI-powered document question-answering system using RAG",
        client_questions=[
            {
                "question": "What type of documents will users upload?"
            },
            {
                "question": "Should the system answer questions based only on uploaded documents?"
            },
            {
                "question": "Does the system need to show the source document for each answer?"
            },
            {
                "question": "How many documents should the system support?"
            }
        ],
        allowed_majors=[
            {
                "major_id": "major-1",
                "name": "Information Technology"
            },
            {
                "major_id": "major-2",
                "name": "Computer Science"
            }
        ],
        allowed_categories=[
            {
                "category_id": "category-1",
                "major_id": "major-1",
                "name": "Backend Development"
            },
            {
                "category_id": "category-2",
                "major_id": "major-2",
                "name": "Artificial Intelligence"
            },
            {
                "category_id": "category-3",
                "major_id": "major-2",
                "name": "Data Science"
            }
        ],
        available_skills=[
            {
                "skill_id": "skill-1",
                "name": "Python"
            },
            {
                "skill_id": "skill-2",
                "name": "FastAPI"
            },
            {
                "skill_id": "skill-3",
                "name": "PostgreSQL"
            },
            {
                "skill_id": "skill-4",
                "name": "Docker"
            }
        ]
    )
    
    print("Sending generation request to AI Job Post Service...")
    response = await service.generate_job_description(request)
    print("\n--- GENERATED RESPONSE ---")
    print(f"Title: {response.title}")
    print(f"Major ID: {response.major_id}")
    print(f"Category ID: {response.category_id}")
    print(f"System Skill IDs: {response.system_skill_ids}")
    print(f"Custom Skills: {response.custom_skills}")
    print("\n--- GENERATED DESCRIPTION ---\n")
    print(response.description)
    print("\n-----------------------------\n")
    print(f"Is AI Generated: {response.is_ai_generated}")

if __name__ == "__main__":
    asyncio.run(test_generation())
