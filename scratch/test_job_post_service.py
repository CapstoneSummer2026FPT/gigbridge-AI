import asyncio
import sys
import os

# Adjust path to import app modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.schemas.job_posts import JobPostGenerationRequest, QuestionAnswerPair
from app.services.job_posts import get_job_post_service

async def test_generation():
    service = get_job_post_service()
    
    # Define a request payload
    request = JobPostGenerationRequest(
        title="Senior React Developer",
        category="Web Development",
        skills=["React", "TypeScript", "Redux", "Tailwind CSS"],
        client_questions_and_freelancer_answers=[
            QuestionAnswerPair(
                question="Have you built complex interactive dashboards before?",
                answer="Yes, I have developed multiple analytics dashboards using React, D3.js, and Redux with real-time WebSocket updates."
            ),
            QuestionAnswerPair(
                question="What is your experience with TypeScript?",
                answer="I have used TypeScript for over 4 years on production-grade projects, enforcing strict type checking and custom utility types."
            )
        ]
    )
    
    print("Sending generation request to AI Job Post Service...")
    response = await service.generate_job_description(request)
    print("\n--- GENERATED DESCRIPTION ---\n")
    print(response.description)
    print("\n-----------------------------\n")
    print(f"Is AI Generated: {response.is_ai_generated}")

if __name__ == "__main__":
    asyncio.run(test_generation())
