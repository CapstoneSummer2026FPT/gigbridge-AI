import asyncio
import sys
import os

# Adjust path to import app modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.schemas.job_posts import JobPostGenerationRequest
from app.services.job_posts import get_job_post_service

async def test_generation():
    service = get_job_post_service()
    
    # Define a request payload with client_questions and allowed_categories
    request = JobPostGenerationRequest(
        client_questions=[
            "Have you built complex interactive dashboards before using React, TypeScript and Redux?",
            "What is your experience with setting up Tailwind CSS and layout frameworks in Next.js?",
            "Can you write clean, reusable custom hooks and components that adhere to strict type checks?"
        ],
        allowed_categories=[
            {
                "categories_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", 
                "name": "Software Development",
                "is_active": True,
                "parent_category_id": None
            },
            {
                "categories_id": "cb1c7fa1-e63d-4299-8d76-f831bfa2833a", 
                "name": "Frontend Development",
                "is_active": True,
                "parent_category_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
            },
            {
                "categories_id": "97e68cfb-6078-4395-8d59-cf2c125df93e", 
                "name": "Legacy COBOL Development",
                "is_active": False,
                "parent_category_id": None
            }
        ]
    )
    
    print("Sending generation request to AI Job Post Service...")
    response = await service.generate_job_description(request)
    print("\n--- GENERATED RESPONSE ---")
    print(f"Title: {response.title}")
    print(f"Category ID: {response.category_id}")
    print(f"Category Name: {response.category_name}")
    print(f"Skills: {response.skills}")
    print("\n--- GENERATED DESCRIPTION ---\n")
    print(response.description)
    print("\n-----------------------------\n")
    print(f"Is AI Generated: {response.is_ai_generated}")

if __name__ == "__main__":
    asyncio.run(test_generation())
