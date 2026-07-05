import requests
import json

url = "http://localhost:8000/api/ai/job-posts/generate"
headers = {
    "X-API-Key": "dev-key-please-change-in-env",
    "Content-Type": "application/json"
}

payload = {
    "client_questions": [
        {"question": "What is the primary programming language for the backend?"},
        {"question": "Do we need a database?"}
    ],
    "allowed_majors": [
        {"major_id": "major-1", "name": "Computer Science"}
    ],
    "allowed_categories": [
        {"category_id": "category-1", "major_id": "major-1", "name": "Software Engineering"}
    ],
    "available_skills": [
        {"skill_id": "skill-1", "name": "Python"},
        {"skill_id": "skill-2", "name": "PostgreSQL"}
    ]
}

try:
    print("Sending POST request to AI Server...")
    response = requests.post(url, headers=headers, json=payload)
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Failed to query AI server: {e}")
