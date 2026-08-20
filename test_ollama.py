import requests

url = "http://localhost:11434/api/generate"

payload = {
    "model": "qwen2.5-coder:7b",
    "prompt": 'Return JSON only: {"ok": true}',
    "stream": False,
    "format": "json",
    "options": {
        "temperature": 0,
        "num_predict": 100,
    },
}

print("Sending request...")

try:
    response = requests.post(
        url,
        json=payload,
        timeout=60,
    )

    print("Status:", response.status_code)
    print("Response:")
    print(response.text)

except requests.exceptions.Timeout:
    print("❌ Ollama request timed out")

except requests.exceptions.ConnectionError:
    print("❌ Could not connect to Ollama")

except requests.exceptions.RequestException as e:
    print("❌ Request failed:", e)