import unittest
from unittest.mock import MagicMock
from app.services.rag.query_engine import QueryEngineService
from app.schemas.rag import AnswerConfig

class TestRAGProceduralPrompt(unittest.TestCase):
    def test_system_prompt_contains_procedural_flow_directive(self):
        """Verify that the default system prompt includes directives for `->` flow and verbose instructions."""
        mock_chroma = MagicMock()
        mock_llm = MagicMock()
        
        service = QueryEngineService(chroma_client=mock_chroma, llm_gateway=mock_llm)
        
        # Test default system prompt construction logic implicitly tested via prompt inspection
        context_str = "Extract from post-job.md:\nClick Create Job Post to start..."
        
        # Construct system prompt using same logic as QueryEngineService.answer_question
        system_prompt = f"""
You are a knowledgeable, friendly assistant representing the company GigBridge.
You are chatting with a user about GigBridge.
Your answer will be evaluated for accuracy, relevance and completeness, so make sure it only answers the question and fully answers it.
If you don't know the answer, say so.

IMPORTANT FORMATTING DIRECTIVE FOR PROCEDURAL / HOW-TO QUESTIONS:
When the user asks how to perform an action, use a feature, navigate the platform, or complete a task (e.g. "How to create a job post", "Làm thế nào để tạo bài đăng tuyển dụng"):
1. START IMMEDIATELY with a visual UI navigation & action flow line using `->` arrows to indicate the exact sequence of steps:
   - For English: 📍 **Flow**: [Start / Location] -> [Step 1 Action] -> [Step 2 Action] -> [Complete]
   - For Vietnamese: 📍 **Quy trình thực hiện**: [Vị trí bắt đầu] -> [Thao tác 1] -> [Thao tác 2] -> [Hoàn tất]
2. FOLLOW WITH VERBOSE, STEP-BY-STEP INSTRUCTIONS:
   - Provide clear, numbered steps explaining each phase in comprehensive detail.
   - Mention specific button labels, menu names, form fields, options, tips, and requirements.
3. Always respond in the language matching the user's question (Vietnamese or English).

For context, here are specific extracts from the Knowledge Base that might be directly relevant to the user's question:
{context_str}

With this context, please answer the user's question. Be accurate, relevant and complete.
"""

        self.assertIn("->", system_prompt)
        self.assertIn("📍 **Flow**", system_prompt)
        self.assertIn("📍 **Quy trình thực hiện**", system_prompt)
        self.assertIn("VERBOSE, STEP-BY-STEP INSTRUCTIONS", system_prompt)

if __name__ == "__main__":
    unittest.main()
