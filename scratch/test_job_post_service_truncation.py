import unittest
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Adjust path to import app modules correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.schemas.job_posts import JobPostGenerationRequest, JobPostGenerationResponse
from app.services.job_posts import JobPostService

class TestJobPostServiceTruncation(unittest.IsolatedAsyncioTestCase):
    async def test_truncation_when_system_skills_exceed_10(self):
        # Arrange
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock()
        
        # Prepare mock response JSON with 12 system skills and 3 custom skills
        mock_response = JobPostGenerationResponse(
            title="AI Engineer",
            major_id="major-1",
            category_id="category-1",
            system_skill_ids=[f"skill-{i}" for i in range(12)],
            custom_skills=["custom-1", "custom-2", "custom-3"],
            description="Detailed job description",
            is_ai_generated=True
        )
        mock_llm.generate.return_value = mock_response.model_dump_json()

        mock_memory = MagicMock()
        mock_memory.save_domain_context = AsyncMock()
        
        mock_prompt = MagicMock()
        mock_prompt.render_prompt = MagicMock(return_value="rendered prompt")

        service = JobPostService(
            llm_gateway=mock_llm,
            memory_manager=mock_memory,
            prompt_manager=mock_prompt
        )

        request = JobPostGenerationRequest(
            client_questions=[],
            allowed_majors=[],
            allowed_categories=[],
            available_skills=[]
        )

        # Act
        result = await service.generate_job_description(request)

        # Assert
        self.assertEqual(len(result.system_skill_ids), 10)
        self.assertEqual(len(result.custom_skills), 0)
        self.assertEqual(result.system_skill_ids, [f"skill-{i}" for i in range(10)])

    async def test_truncation_when_combined_skills_exceed_10(self):
        # Arrange
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock()
        
        # Prepare mock response JSON with 7 system skills and 5 custom skills (Total = 12)
        mock_response = JobPostGenerationResponse(
            title="AI Engineer",
            major_id="major-1",
            category_id="category-1",
            system_skill_ids=[f"skill-{i}" for i in range(7)],
            custom_skills=["custom-1", "custom-2", "custom-3", "custom-4", "custom-5"],
            description="Detailed job description",
            is_ai_generated=True
        )
        mock_llm.generate.return_value = mock_response.model_dump_json()

        mock_memory = MagicMock()
        mock_memory.save_domain_context = AsyncMock()
        
        mock_prompt = MagicMock()
        mock_prompt.render_prompt = MagicMock(return_value="rendered prompt")

        service = JobPostService(
            llm_gateway=mock_llm,
            memory_manager=mock_memory,
            prompt_manager=mock_prompt
        )

        request = JobPostGenerationRequest(
            client_questions=[],
            allowed_majors=[],
            allowed_categories=[],
            available_skills=[]
        )

        # Act
        result = await service.generate_job_description(request)

        # Assert
        self.assertEqual(len(result.system_skill_ids), 7)
        self.assertEqual(len(result.custom_skills), 3)
        self.assertEqual(result.system_skill_ids, [f"skill-{i}" for i in range(7)])
        self.assertEqual(result.custom_skills, ["custom-1", "custom-2", "custom-3"])

    async def test_no_truncation_when_total_skills_less_than_10(self):
        # Arrange
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock()
        
        # Prepare mock response JSON with 5 system skills and 3 custom skills (Total = 8)
        mock_response = JobPostGenerationResponse(
            title="AI Engineer",
            major_id="major-1",
            category_id="category-1",
            system_skill_ids=[f"skill-{i}" for i in range(5)],
            custom_skills=["custom-1", "custom-2", "custom-3"],
            description="Detailed job description",
            is_ai_generated=True
        )
        mock_llm.generate.return_value = mock_response.model_dump_json()

        mock_memory = MagicMock()
        mock_memory.save_domain_context = AsyncMock()
        
        mock_prompt = MagicMock()
        mock_prompt.render_prompt = MagicMock(return_value="rendered prompt")

        service = JobPostService(
            llm_gateway=mock_llm,
            memory_manager=mock_memory,
            prompt_manager=mock_prompt
        )

        request = JobPostGenerationRequest(
            client_questions=[],
            allowed_majors=[],
            allowed_categories=[],
            available_skills=[]
        )

        # Act
        result = await service.generate_job_description(request)

        # Assert
        self.assertEqual(len(result.system_skill_ids), 5)
        self.assertEqual(len(result.custom_skills), 3)
        self.assertEqual(result.system_skill_ids, [f"skill-{i}" for i in range(5)])
        self.assertEqual(result.custom_skills, ["custom-1", "custom-2", "custom-3"])

if __name__ == "__main__":
    unittest.main()
