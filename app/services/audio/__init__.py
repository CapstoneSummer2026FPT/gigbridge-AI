"""
PURPOSE: Audio services package facade providing audio validation, decoding, chunking, stitching, routing, and voice session management.
IMPORTANCE: Critical — Primary entrypoint for audio processing domain services across API routes and voice engines.
READING FLOW: app/services/audio/audio_processor.py -> app/services/audio/audio_chunker.py -> app/services/audio/tts_audio_stitcher.py -> app/services/audio/tts_segment_router.py -> app/services/audio/voice.py -> app/services/audio/__init__.py
"""

from app.services.audio.audio_processor import AudioProcessor
from app.services.audio.audio_chunker import AudioChunker, AudioChunk
from app.services.audio.tts_audio_stitcher import TTSAudioStitcher
from app.services.audio.tts_segment_router import TTSSegmentRouter, TTSSegment
from app.services.audio.voice import VoiceService, get_voice_service

__all__ = [
    "AudioProcessor",
    "AudioChunker",
    "AudioChunk",
    "TTSAudioStitcher",
    "TTSSegmentRouter",
    "TTSSegment",
    "VoiceService",
    "get_voice_service",
]
