import json
import re

import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:7b"

EXPLANATION_TIMEOUT = 120
COMPLETE_FIX_TIMEOUT = 180


# ============================================================
# Common JSON parser
# ============================================================

def parse_ai_json(ai_response: str):
    """
    Convert Ollama's response into a Python dictionary.

    Handles:
    1. Normal JSON
    2. JSON wrapped in markdown
    3. JSON embedded inside additional text
    """

    if not ai_response:
        return None

    # --------------------------------------------------------
    # Attempt 1: Direct JSON parsing
    # --------------------------------------------------------

    try:
        parsed = json.loads(ai_response)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # Attempt 2: Remove markdown fences
    # --------------------------------------------------------

    cleaned = re.sub(
        r"```(?:json)?",
        "",
        ai_response,
        flags=re.IGNORECASE,
    )

    cleaned = cleaned.replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # Attempt 3: Find JSON object inside response
    # --------------------------------------------------------

    match = re.search(
        r"\{.*\}",
        ai_response,
        re.DOTALL,
    )

    if match:
        try:
            parsed = json.loads(match.group())

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError:
            pass

    return None


# ============================================================
# Normal AI explanation request
# ============================================================

def ask_ollama(prompt: str):
    """
    Send a normal AI explanation request to Ollama.
    """

    try:
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
            timeout=EXPLANATION_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        ai_response = data.get(
            "response",
            "",
        ).strip()

        if not ai_response:
            return {
                "why": "The AI returned an empty response.",
                "fix": "Try running the review again.",
                "secure_code": "",
            }

        parsed = parse_ai_json(ai_response)

        if parsed is not None:
            return {
                "why": str(
                    parsed.get("why", "")
                ),
                "fix": str(
                    parsed.get("fix", "")
                ),
                "secure_code": str(
                    parsed.get("secure_code", "")
                ),
            }

        return {
            "why": (
                "The AI response could not be "
                "parsed as JSON."
            ),
            "fix": (
                "The AI returned an invalid "
                "response format."
            ),
            "secure_code": "",
        }

    except requests.exceptions.Timeout:
        print(
            "\n⚠️ Ollama explanation request timed out."
        )

        return {
            "why": (
                "The AI explanation request timed out."
            ),
            "fix": (
                "Ollama took too long to generate "
                "the explanation. Try again."
            ),
            "secure_code": "",
        }

    except requests.exceptions.ConnectionError:
        print(
            "\n⚠️ Could not connect to Ollama."
        )

        return {
            "why": (
                "The AI service could not be reached."
            ),
            "fix": (
                "Make sure Ollama is running and "
                "the qwen2.5-coder:7b model is available."
            ),
            "secure_code": "",
        }

    except requests.exceptions.HTTPError as exc:
        print(
            f"\n⚠️ Ollama HTTP error: {exc}"
        )

        return {
            "why": (
                "The Ollama service returned an HTTP error."
            ),
            "fix": (
                "Check that Ollama is running and "
                "the requested model is available."
            ),
            "secure_code": "",
        }

    except requests.exceptions.RequestException as exc:
        print(
            f"\n⚠️ Ollama request failed: {exc}"
        )

        return {
            "why": (
                "The AI service request failed."
            ),
            "fix": (
                "Check the Ollama service and "
                "try the review again."
            ),
            "secure_code": "",
        }

    except (json.JSONDecodeError, ValueError) as exc:
        print(
            f"\n⚠️ Invalid Ollama response: {exc}"
        )

        return {
            "why": (
                "Ollama returned an invalid response."
            ),
            "fix": (
                "Try running the review again."
            ),
            "secure_code": "",
        }


# ============================================================
# Complete AI fix request
# ============================================================

def ask_ollama_complete_fix(prompt: str):
    """
    Ask Ollama to generate ONE complete corrected
    version of the original Python program.

    If Ollama fails, times out, returns invalid JSON,
    or returns empty code, automatic correction is blocked.
    """

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0,
                    "num_predict": 800,
                },
            },
            timeout=COMPLETE_FIX_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        ai_response = data.get(
            "response",
            "",
        ).strip()

        # ====================================================
        # Empty response
        # ====================================================

        if not ai_response:
            print(
                "\n⚠️ Ollama returned an empty "
                "complete-fix response."
            )

            return {
                "summary": (
                    "The AI returned an empty response."
                ),
                "fix": (
                    "The AI could not generate a "
                    "complete corrected program."
                ),
                "corrected_code": "",
                "manual_review_required": True,
            }

        # ====================================================
        # Parse JSON
        # ====================================================

        parsed = parse_ai_json(ai_response)

        if parsed is None:
            print(
                "\n⚠️ Ollama returned invalid JSON."
            )

            print(
                "\nRaw AI response:"
            )

            print(ai_response)

            return {
                "summary": (
                    "The AI response could not "
                    "be parsed as JSON."
                ),
                "fix": (
                    "The AI returned an invalid "
                    "response format. Manual review "
                    "is required."
                ),
                "corrected_code": "",
                "manual_review_required": True,
            }

        corrected_code = str(
            parsed.get(
                "corrected_code",
                "",
            )
        ).strip()

        # ====================================================
        # AI explicitly returned no correction
        # ====================================================

        if not corrected_code:
            return {
                "summary": str(
                    parsed.get(
                        "summary",
                        "Manual review is required.",
                    )
                ),
                "fix": str(
                    parsed.get(
                        "fix",
                        "The AI did not provide a safe "
                        "complete correction.",
                    )
                ),
                "corrected_code": "",
                "manual_review_required": True,
            }

        # ====================================================
        # Valid AI response
        # ====================================================

        return {
            "summary": str(
                parsed.get(
                    "summary",
                    "",
                )
            ),
            "fix": str(
                parsed.get(
                    "fix",
                    "",
                )
            ),
            "corrected_code": corrected_code,
            "manual_review_required": False,
        }

    # ========================================================
    # Timeout
    # ========================================================

    except requests.exceptions.Timeout:
        print(
            "\n⚠️ Ollama complete-fix "
            "generation timed out."
        )

        return {
            "summary": (
                "AI fix generation timed out."
            ),
            "fix": (
                "Ollama did not generate a complete "
                "corrected program within the allowed "
                "time. Manual review is required."
            ),
            "corrected_code": "",
            "manual_review_required": True,
        }

    # ========================================================
    # Connection error
    # ========================================================

    except requests.exceptions.ConnectionError:
        print(
            "\n⚠️ Could not connect to Ollama."
        )

        return {
            "summary": (
                "The AI service could not be reached."
            ),
            "fix": (
                "Make sure Ollama is running and "
                "the qwen2.5-coder:7b model is available."
            ),
            "corrected_code": "",
            "manual_review_required": True,
        }

    # ========================================================
    # HTTP error
    # ========================================================

    except requests.exceptions.HTTPError as exc:
        print(
            f"\n⚠️ Ollama HTTP error: {exc}"
        )

        return {
            "summary": (
                "The Ollama service returned an HTTP error."
            ),
            "fix": (
                "Check that Ollama is running and "
                "the qwen2.5-coder:7b model is available."
            ),
            "corrected_code": "",
            "manual_review_required": True,
        }

    # ========================================================
    # Other request errors
    # ========================================================

    except requests.exceptions.RequestException as exc:
        print(
            f"\n⚠️ Ollama complete-fix request "
            f"failed: {exc}"
        )

        return {
            "summary": (
                "The AI service request failed."
            ),
            "fix": (
                "Check the Ollama service and "
                "try the review again."
            ),
            "corrected_code": "",
            "manual_review_required": True,
        }

    # ========================================================
    # Invalid JSON returned by HTTP response
    # ========================================================

    except (json.JSONDecodeError, ValueError) as exc:
        print(
            f"\n⚠️ Invalid Ollama response: {exc}"
        )

        return {
            "summary": (
                "The AI service returned an invalid response."
            ),
            "fix": (
                "Try running the review again. "
                "Manual review is required if the problem persists."
            ),
            "corrected_code": "",
            "manual_review_required": True,
        }

    # ========================================================
    # Unexpected error
    # ========================================================

    except Exception as exc:
        print(
            f"\n⚠️ Unexpected Ollama error: {exc}"
        )

        return {
            "summary": (
                "An unexpected AI service error occurred."
            ),
            "fix": (
                "Review the backend logs and "
                "try the request again."
            ),
            "corrected_code": "",
            "manual_review_required": True,
        }