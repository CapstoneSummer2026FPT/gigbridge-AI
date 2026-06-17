import asyncio
import sys
import os

# Adjust path to import app modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.schemas.job_posts import JobPostGenerationRequest
from app.services.job_posts import get_job_post_service

async def test_generation():
    service = get_job_post_service()
    
    # Define a request payload with just client_questions
    request = JobPostGenerationRequest(
        client_questions=[
            "Have you built complex interactive dashboards before using React, TypeScript and Redux?",
            "What is your experience with setting up Tailwind CSS and layout frameworks in Next.js?",
            "Can you write clean, reusable custom hooks and components that adhere to strict type checks?"
        ]
    )
    
    print("Sending generation request to AI Job Post Service...")
    response = await service.generate_job_description(request)
    print("\n--- GENERATED RESPONSE ---")
    print(f"Title: {response.title}")
    print(f"Category: {response.catgory}")
    print(f"Skills: {response.skills}")
    print("\n--- GENERATED DESCRIPTION ---\n")
    print(response.description)
    print("\n-----------------------------\n")
    print(f"Is AI Generated: {response.is_ai_generated}")

if __name__ == "__main__":
    asyncio.run(test_generation())
