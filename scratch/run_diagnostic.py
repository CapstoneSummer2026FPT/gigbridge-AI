import os
import sys
import time
import requests
import json
import subprocess

# Define paths
project_root = r"c:\Users\OS\Documents\GitHub\ProjectCapstone"
controller_path = os.path.join(
    project_root, 
    "Gigbridge_ProjectCapstone", 
    "GigBridge", 
    "Project_API", 
    "Controllers", 
    "Client", 
    "ClientJobPostsController.cs"
)
backend_dir = os.path.join(project_root, "Gigbridge_ProjectCapstone", "GigBridge")

# 1. Read original controller
print("Reading original controller code...")
with open(controller_path, "r", encoding="utf-8") as f:
    original_code = f.read()

# 2. Modify GenerateJobDescription to be AllowAnonymous and bypass user check
modified_code = original_code.replace(
    '[HttpPost("ai/generate")]\n    public async Task<IActionResult> GenerateJobDescription([FromBody] GenerateJobDescriptionCommand command)',
    '[HttpPost("ai/generate")]\n    [AllowAnonymous]\n    public async Task<IActionResult> GenerateJobDescription([FromBody] GenerateJobDescriptionCommand command)'
)

# Replace TryGetCurrentUserId check
old_check = """        if (!TryGetCurrentUserId(out _))
        {
            return InvalidTokenResponse();
        }"""

if old_check in modified_code:
    modified_code = modified_code.replace(old_check, "        // Bypassed check for diagnosis")
else:
    # Try different spacing / line endings
    modified_code = modified_code.replace("if (!TryGetCurrentUserId(out _))", "// Bypassed check")

print("Writing modified controller code...")
with open(controller_path, "w", encoding="utf-8") as f:
    f.write(modified_code)

backend_process = None
try:
    # 3. Start C# Backend
    print("Starting C# Backend in background...")
    # Using launch-profile http which binds to port 5222
    backend_process = subprocess.Popen(
        ["dotnet", "run", "--project", "Project_API/Project_API.csproj", "--launch-profile", "http"],
        cwd=backend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 4. Wait for backend to start up
    print("Waiting for backend to bind to port 5222...")
    for i in range(20):
        try:
            r = requests.get("http://localhost:5222/health", timeout=1)
            if r.status_code == 200:
                print(f"Backend is online after {i} seconds.")
                break
        except requests.RequestException:
            pass
        time.sleep(1)
    
    # 5. Send POST request to C# backend
    url = "http://localhost:5222/api/JobPosts/ai/generate"
    payload = {
        "vettingQuestions": [
            "What type of documents will users upload?",
            "How many documents should the system support?"
        ]
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    print("\nSending POST request to C# backend GenerateJobDescription endpoint...")
    response = requests.post(url, headers=headers, json=payload)
    print(f"Response Status Code: {response.status_code}")
    print("Response Content:")
    try:
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print(response.text)

except Exception as e:
    print(f"Error occurred: {e}")

finally:
    # 6. Restore controller code
    print("Restoring controller code to original...")
    with open(controller_path, "w", encoding="utf-8") as f:
        f.write(original_code)
    
    # 7. Stop temporary backend process
    if backend_process:
        print("Stopping C# backend process...")
        backend_process.terminate()
        try:
            stdout, stderr = backend_process.communicate(timeout=5)
            print("\nBackend logs from the run:")
            print(stdout)
            if stderr:
                print("Backend error logs:")
                print(stderr)
        except subprocess.TimeoutExpired:
            backend_process.kill()
            print("Backend killed.")
