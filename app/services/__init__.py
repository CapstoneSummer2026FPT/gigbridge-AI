"""
PURPOSE: Services root package facade aggregating domain services (audio, interviews, job_posts, matching, rag).
IMPORTANCE: High — Root module entrypoint for domain services.
READING FLOW: app/services/audio -> app/services/interviews -> app/services/job_posts -> app/services/matching -> app/services/rag -> app/services/__init__.py
"""

from app.services.audio import AudioProcessor, VoiceService, get_voice_service
from app.services.interviews import InterviewService, get_interview_service
from app.services.job_posts import JobPostService, get_job_post_service
from app.services.job_posts.analysis import AnalysisService, get_analysis_service
from app.services.matching import MatchingService, JobMatchingService, FreelancerMatchingService, PhoneticMatcher, TypoMatcher
from app.services.rag import RAGService, get_rag_service, MemoryManager, get_memory_manager, HotwordResolver, get_hotword_resolver, EvidenceEvaluatorService

__all__ = [
    "AudioProcessor",
    "VoiceService",
    "get_voice_service",
    "InterviewService",
    "get_interview_service",
    "JobPostService",
    "get_job_post_service",
    "AnalysisService",
    "get_analysis_service",
    "MatchingService",
    "JobMatchingService",
    "FreelancerMatchingService",
    "PhoneticMatcher",
    "TypoMatcher",
    "RAGService",
    "get_rag_service",
    "MemoryManager",
    "get_memory_manager",
    "HotwordResolver",
    "get_hotword_resolver",
    "EvidenceEvaluatorService",
]
