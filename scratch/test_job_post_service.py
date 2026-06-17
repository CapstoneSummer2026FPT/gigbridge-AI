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
    request = JobPostGenerationRequest(
        title="Build a real-time analytics dashboard",
        client_questions=[
            {
                "question": "What type of application do you need?"
            }
        ],
        allowed_majors=[
            {
                "major_id": "major-1",
                "name": "Information Technology"
            }
        ],
        allowed_categories=[
            {
                "category_id": "category-1",
                "major_id": "major-1",
                "name": "Web Development"
            },
            {
                "category_id": "category-2",
                "major_id": "major-1",
                "name": "Mobile Development"
            }
        ],
        available_skills=[
            {
                "skill_id": "skill-1",
                "name": "React"
            },
            {
                "skill_id": "skill-2",
                "name": "TypeScript"
            },
            {
                "skill_id": "skill-3",
                "name": "WebSocket"
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
