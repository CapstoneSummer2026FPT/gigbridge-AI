import requests
import json

base_url = "http://localhost:5222"

# 1. Login to C# backend
login_url = f"{base_url}/api/auth/login"
login_payload = {
    "email": "huy.le@fpt.com.vn",
    "password": "Password123!"
}

print("Attempting to login to C# backend...")
try:
    login_response = requests.post(login_url, json=login_payload)
    print(f"Login Response Status: {login_response.status_code}")
    login_data = login_response.json()
    print("Login Response:")
    print(json.dumps(login_data, indent=2))
    
    if login_response.status_code != 200 or not login_data.get("success"):
        print("Login failed. Cannot proceed with AI generation test.")
        exit(1)
        
    token = login_data["data"]["accessToken"]
    print("Successfully retrieved access token.")
    
    # 2. Call AI generate job post endpoint
    generate_url = f"{base_url}/api/JobPosts/ai/generate"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    generate_payload = {
        "vettingQuestions": [
            "What type of documents will users upload?",
            "How many documents should the system support?"
        ]
    }
    
    print("\nSending AI job post generation request to C# backend...")
    gen_response = requests.post(generate_url, headers=headers, json=generate_payload)
    print(f"AI Generation Status: {gen_response.status_code}")
    try:
        gen_data = gen_response.json()
        print("AI Generation Response:")
        print(json.dumps(gen_data, indent=2))
    except Exception as e:
        print(f"Could not parse JSON response: {e}")
        print(f"Raw Response: {gen_response.text}")
        
except Exception as e:
    print(f"Error during communication: {e}")
