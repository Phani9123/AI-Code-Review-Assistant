import requests

from backend.app.services.ollama_service import (
    MODEL_NAME,
    OLLAMA_URL,
)


source_code = """
def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)

numbers = []
print(calculate_average(numbers))
"""


prompt = f"""
You are a senior Python code reviewer.

Review this code for real bugs, security problems,
performance problems, edge cases, concurrency problems,
resource problems, and incorrect behavior.

Only report issues directly supported by the source code.
Do not invent requirements.

Return ONLY valid JSON.

Use exactly this schema:

{{
    "issues": [
        {{
            "category": "bug",
            "severity": "HIGH",
            "confidence": "HIGH",
            "line": 4,
            "end_line": 4,
            "problem": "Short description",
            "evidence": "Code demonstrating the issue",
            "why": "Why it is a problem",
            "verification": "How the issue can be demonstrated",
            "change": "Specific change required"
        }}
    ]
}}

Allowed categories:
bug
security
performance
edge_case
concurrency
resource
database
maintainability
testing
other

Allowed severity:
CRITICAL
HIGH
MEDIUM
LOW

Allowed confidence:
HIGH
MEDIUM
LOW

SOURCE CODE:

{source_code}
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
            "num_predict": 400,
        },
    },
    timeout=60,
)

response.raise_for_status()

data = response.json()

print("\nStatus:", response.status_code)

print("\n========== OLLAMA RESPONSE ==========")

print(data.get("response", ""))

print("\n========== PERFORMANCE ==========")

print(
    "Total duration:",
    data.get("total_duration"),
)

print(
    "Prompt tokens:",
    data.get("prompt_eval_count"),
)

print(
    "Output tokens:",
    data.get("eval_count"),
)