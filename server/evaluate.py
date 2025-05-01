import requests

PISTON_URL = "https://piston-backend.fly.dev/api/v2/execute"  

def run_code(code, language, expected_output):
    payload = {
        "language": language,
        "version": "*",
        "files": [{"name": "main", "content": code}]
    }

    response = requests.post(PISTON_URL, json=payload)
    result = response.json()

    actual_output = result.get("run", {}).get("stdout", "").strip()
    correct = actual_output == expected_output.strip()
    score = max(0, 1000 - len(code)) if correct else 0

    return {
        "correct": correct,
        "output": actual_output,
        "score": score
    }
