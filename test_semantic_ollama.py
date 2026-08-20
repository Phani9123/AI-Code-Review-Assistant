import requests

from backend.app.services.ollama_service import (
    MODEL_NAME,
    OLLAMA_URL,
)


prompt = """
Review this Python code for one important bug.

Code:

def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)

Return ONLY JSON:

{
  "issues": [
    {
      "problem": "...",
      "line": 3,
      "change": "..."
    }
  ]
}
"""


print("Sending request...")

response = requests.post(
    OLLAMA_URL,
    json={
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 300,
        },
    },
    timeout=60,
)

response.raise_for_status()

print("Status:", response.status_code)
print("Response:")
print(response.text)