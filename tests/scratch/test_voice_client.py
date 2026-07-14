import sys
import httpx
import struct
import numpy as np

# Configuration
SERVER_URL = "http://localhost:8000"
API_KEY = "your-secure-shared-api-key-here"  # Match this with AI_SERVER_API_KEY in .env

headers = {
    "X-API-Key": API_KEY
}

def generate_dummy_wav() -> bytes:
    """Generate 2 seconds of 440Hz sine wave as WAV 16kHz mono PCM bytes."""
    sample_rate = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Generate audio: sine wave with some amplitude to avoid silence detection
    samples = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
    
    num_samples = len(samples)
    data_size = num_samples * 2
    header = bytearray()
    header.extend(b"RIFF")
    header.extend(struct.pack("<I", 36 + data_size))
    header.extend(b"WAVEfmt ")
    header.extend(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    header.extend(b"data")
    header.extend(struct.pack("<I", data_size))
    return bytes(header) + samples.tobytes()

async def test_voice_flow():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health check
        print("Checking server health...")
        try:
            r = await client.get(f"{SERVER_URL}/health")
            if r.status_code != 200:
                print(f"Health check failed with status: {r.status_code}")
                return
            print("Server is healthy:", r.json())
        except Exception as e:
            print(f"Could not connect to server at {SERVER_URL}. Make sure it is running! Error: {e}")
            return

        # 2. Start Interview Session
        print("\nStarting voice interview...")
        payload = {
            "job_id": "test_job_001",
            "freelancer_id": "test_free_001",
            "job_title": "React Frontend Developer",
            "job_description": "Build a bilingual marketplace UI with React, TypeScript, Vite, and REST API integration.",
            "job_skills": ["React", "TypeScript", "Vite", "REST API"],
            "mode": "voice",
            "language": "vi"
        }
        r = await client.post(f"{SERVER_URL}/api/ai/interviews/start", json=payload, headers=headers)
        if r.status_code != 201:
            print(f"Failed to start interview: {r.status_code} - {r.text}")
            return
        
        start_data = r.json()
        print("Interview started successfully!")
        session_id = start_data["data"]["session_id"]
        question = start_data["data"]["question_text"]
        print(f"Session ID: {session_id}")
        print(f"First Question: '{question}'")

        # 3. Transcribe Audio (Upload voice answer)
        print("\nGenerating dummy WAV file & uploading for transcription...")
        wav_data = generate_dummy_wav()
        
        files = {
            "audio_file": ("test_speech.wav", wav_data, "audio/wav")
        }
        data = {
            "session_id": session_id,
            "language": "vi"
        }
        
        r = await client.post(
            f"{SERVER_URL}/api/ai/interviews/transcribe-audio",
            data=data,
            files=files,
            headers=headers
        )
        if r.status_code != 200:
            print(f"Transcription failed: {r.status_code} - {r.text}")
            return
        
        transcribe_data = r.json()
        print("Transcription complete!")
        transcript = transcribe_data["data"]["transcript"]
        stt_provider = transcribe_data["data"]["stt_provider"]
        print(f"Transcript: '{transcript}'")
        print(f"STT Provider: {stt_provider}")

        # 4. Confirm Answer
        print("\nConfirming transcribed answer...")
        confirm_payload = {
            "session_id": session_id,
            "corrected_text": transcript
        }
        r = await client.post(f"{SERVER_URL}/api/ai/interviews/confirm-answer", json=confirm_payload, headers=headers)
        if r.status_code != 200:
            print(f"Confirmation failed: {r.status_code} - {r.text}")
            return
        
        confirm_data = r.json()
        print("Answer confirmed!")
        next_question = confirm_data["data"]["question_text"]
        print(f"Next Question: '{next_question}'")
        print("Test completed successfully!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_voice_flow())
