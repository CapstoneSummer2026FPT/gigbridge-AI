import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import BaseModel

from answer import answer_question as cli_answer_question, RelevanceCheck as CLIRelevanceCheck
from app.services.rag import RAGService, RelevanceCheck as ServiceRelevanceCheck
from app.api.schemas.rag import AnswerConfig, AnswerResult

# Mock Response Object for litellm
class MockChoiceMessage(BaseModel):
    content: str

class MockChoice(BaseModel):
    message: MockChoiceMessage

class MockCompletionResponse(BaseModel):
    choices: list[MockChoice]


def test_cli_unrelated_query_vietnamese():
    # Setup mock response from relevance check showing it is unrelated in Vietnamese
    mock_relevance = CLIRelevanceCheck(
        related=False,
        topic="sự kiện Thiên An Môn",
        language="vi"
    )
    
    with patch("answer.check_relevance", return_value=mock_relevance):
        answer, chunks = cli_answer_question("chuyện j xảy ra ở thiên an môn")
        
        assert "Xin lỗi, nhưng tôi không có thông tin nào về sự kiện Thiên An Môn" in answer
        assert "Tôi chỉ có thể cung cấp thông tin liên quan đến GigBridge" in answer
        assert chunks == []


def test_cli_unrelated_query_english():
    # Setup mock response from relevance check showing it is unrelated in English
    mock_relevance = CLIRelevanceCheck(
        related=False,
        topic="what happened in Tiananmen",
        language="en"
    )
    
    with patch("answer.check_relevance", return_value=mock_relevance):
        answer, chunks = cli_answer_question("what happened in Tiananmen")
        
        assert "Sorry, but I don't have any information about what happened in Tiananmen" in answer
        assert "I can only provide information related to GigBridge" in answer
        assert chunks == []


@pytest.mark.anyio
async def test_service_unrelated_query_vietnamese():
    # Setup mock response from service relevance check showing it is unrelated in Vietnamese
    mock_relevance = ServiceRelevanceCheck(
        related=False,
        topic="sự kiện Thiên An Môn",
        language="vi"
    )
    
    service = RAGService()
    
    with patch.object(service, "check_relevance", AsyncMock(return_value=mock_relevance)):
        config = AnswerConfig()
        result = await service.answer_question("chuyện j xảy ra ở thiên an môn", config)
        
        assert "Xin lỗi, nhưng tôi không có thông tin nào về sự kiện Thiên An Môn" in result.answer
        assert "Tôi chỉ có thể cung cấp thông tin liên quan đến GigBridge" in result.answer
        assert result.sources == []


@pytest.mark.anyio
async def test_service_unrelated_query_english():
    # Setup mock response from service relevance check showing it is unrelated in English
    mock_relevance = ServiceRelevanceCheck(
        related=False,
        topic="what happened in Tiananmen",
        language="en"
    )
    
    service = RAGService()
    
    with patch.object(service, "check_relevance", AsyncMock(return_value=mock_relevance)):
        config = AnswerConfig()
        result = await service.answer_question("what happened in Tiananmen", config)
        
        assert "Sorry, but I don't have any information about what happened in Tiananmen" in result.answer
        assert "I can only provide information related to GigBridge" in result.answer
        assert result.sources == []


@pytest.mark.anyio
async def test_service_on_topic_query_proceeds():
    # When query is related, it should NOT return the rejection message and should fetch context instead
    mock_relevance = ServiceRelevanceCheck(
        related=True,
        topic="GigBridge features",
        language="en"
    )
    
    service = RAGService()
    
    # Mock retrieval and completion so we don't trigger actual network calls
    with patch.object(service, "check_relevance", AsyncMock(return_value=mock_relevance)):
        with patch.object(service, "fetch_context", AsyncMock(return_value=[])):
            # Mock acompletion for QA
            mock_resp = MockCompletionResponse(
                choices=[MockChoice(message=MockChoiceMessage(content="GigBridge is a great platform."))]
            )
            with patch("app.services.rag.acompletion", AsyncMock(return_value=mock_resp)):
                config = AnswerConfig()
                result = await service.answer_question("Tell me about GigBridge", config)
                
                assert result.answer == "GigBridge is a great platform."
                assert "Sorry, but I don't have any information" not in result.answer
