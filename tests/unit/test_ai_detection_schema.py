import sys
from pydantic import ValidationError
from app.schemas.interviews import InterviewFeedback, GradedQuestion

def test_ai_detection_schema():
    raw_json = """
    {
        "score": 85,
        "summary": "Candidate shows good backend skills. Question 1 flagged as AI generated.",
        "is_ai_generated": true,
        "ai_confidence_score": 0.75,
        "ai_detection_summary": "Question 1 exhibits stereotypical ChatGPT intro and bullet lists.",
        "technical_skills": ["Python", "FastAPI", "PostgreSQL"],
        "soft_skills": ["Structured Communication"],
        "recommended_hire": true,
        "holistic_adjustment": 0,
        "holistic_adjustment_reason": "No penalty applied.",
        "graded_questions": [
            {
                "question_index": 1,
                "question_text": "How do you optimize SQL queries?",
                "question_type": "problem_solving",
                "difficulty": "medium",
                "candidate_answer": "Certainly! Here is a guide...",
                "score": 85,
                "feedback": "Correct SQL optimization techniques.",
                "is_ai_generated": true,
                "ai_confidence_score": 0.85,
                "ai_detection_reason": "Contains overt ChatGPT introductory filler and uniform bullet list structure."
            }
        ]
    }
    """
    
    feedback = InterviewFeedback.model_validate_json(raw_json)
    assert feedback.is_ai_generated is True
    assert feedback.ai_confidence_score == 0.75
    assert "Question 1" in feedback.ai_detection_summary
    assert feedback.graded_questions[0].is_ai_generated is True
    assert feedback.graded_questions[0].ai_confidence_score == 0.85
    assert "ChatGPT" in feedback.graded_questions[0].ai_detection_reason
    print("SUCCESS: InterviewFeedback schema validated successfully with AI detection fields!")

if __name__ == "__main__":
    test_ai_detection_schema()
