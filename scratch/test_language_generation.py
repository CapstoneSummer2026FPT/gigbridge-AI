import asyncio
import sys
import os

# Adjust path to import app modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding='utf-8')
import logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

from app.schemas.job_posts import JobPostGenerationRequest
from app.services.job_posts import get_job_post_service

async def run_test(prompt: str, test_name: str):
    service = get_job_post_service()
    request = JobPostGenerationRequest(
        client_prompt=prompt,
        allowed_majors=[
            {"major_id": "major-1", "name": "Information Technology"},
            {"major_id": "major-2", "name": "Computer Science"}
        ],
        allowed_categories=[
            {"category_id": "category-1", "major_id": "major-1", "name": "Backend Development"},
            {"category_id": "category-2", "major_id": "major-2", "name": "Artificial Intelligence"}
        ],
        available_skills=[
            {"skill_id": "skill-1", "name": "Python"},
            {"skill_id": "skill-2", "name": "FastAPI"}
        ]
    )
    
    print(f"\n==================== {test_name} ====================")
    print(f"Client Prompt: {prompt}\n")
    try:
        response = await service.generate_job_description(request)
        print("Generated Fields:")
        print(f"  Title (should be English): {response.title}")
        print(f"  Custom Skills (should be English): {response.custom_skills}")
        print(f"  Question Recruitment (adapted): {response.question_recruitment}")
        print("  Description (adapted):")
        print(response.description)
    except Exception as e:
        print(f"Error: {e}")

async def main():
    # Test 1: Vietnamese Prompt
    await run_test(
        prompt="Tuyển lập trình viên Backend Python/FastAPI có kinh nghiệm làm việc với cơ sở dữ liệu PostgreSQL và Docker.",
        test_name="Vietnamese Prompt Test"
    )
    
    # Test 2: English Prompt
    await run_test(
        prompt="Looking for a Python/FastAPI backend developer to build a secure document management system using PostgreSQL and Docker.",
        test_name="English Prompt Test"
    )

if __name__ == "__main__":
    asyncio.run(main())
