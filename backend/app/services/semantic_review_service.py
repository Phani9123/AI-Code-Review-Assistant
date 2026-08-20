import time

import requests

from backend.app.services.ollama_service import (
    MODEL_NAME,
    OLLAMA_URL,
    parse_ai_json,
)


# ============================================================
# SEMANTIC REVIEW PROMPT
# ============================================================

def build_semantic_review_prompt(source_code: str) -> str:
    """
    Build a compact semantic-review prompt.

    Ruff and Bandit handle static/deterministic findings.
    The LLM focuses on code behavior and problems requiring
    semantic understanding.
    """

    return f"""
You are a senior Python code reviewer.

Review the ORIGINAL Python code below.

Find real problems that static tools such as Ruff and Bandit
may miss.

Check for:

- logic bugs
- runtime errors
- edge cases
- authentication/authorization bugs
- security vulnerabilities
- inefficient algorithms
- performance problems
- race conditions
- shared mutable state
- resource leaks
- database problems
- API misuse
- exception-handling problems
- important maintainability problems

RULES:

1. Only report problems demonstrated by the source code.
2. Do not invent requirements or business logic.
3. Do not report style preferences.
4. Find ALL meaningful independent issues.
5. Verify the execution path before reporting a bug.
6. Evidence must come from the source code.
7. Use the smallest relevant line range.
8. Do not invent values or function arguments.
9. For undefined names, only fix obvious typos.
10. Do not generate a complete replacement program.

For each issue return:

{{
    "category": "bug",
    "severity": "HIGH",
    "confidence": "HIGH",
    "line": 1,
    "end_line": 1,
    "problem": "Short description",
    "evidence": "Problematic source code",
    "why": "Why it is a problem",
    "verification": "How the issue can be demonstrated",
    "change": "Specific change required"
}}

Categories:
bug, security, performance, edge_case, concurrency,
resource, database, maintainability, testing, other

Severity:
CRITICAL, HIGH, MEDIUM, LOW

Confidence:
HIGH, MEDIUM, LOW

Important examples:

Empty list:

    return total / len(numbers)

If the code calls the function with an empty list,
report the division-by-zero problem.

Mutable default:

    def add_item(item, items=[]):

Report the shared mutable default argument.

Nested loops:

    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):

Report O(n²) performance when the loops perform pairwise
comparisons over the input.

Authentication:

    if username in users:
        if password:
            return True

Report that a non-empty password is accepted without
comparing it with the stored password.

Concurrency:

    counter += 1

If multiple threads modify the same shared counter without
synchronization, report the concurrency risk.

SQL:

    query = f"SELECT ... {{username}} ..."

If user-controlled data is directly inserted into SQL,
report SQL injection.

Return ONLY JSON.

If there are no meaningful issues:

{{
    "issues": []
}}

SOURCE CODE:

{source_code}
"""

# ============================================================
# NORMALIZE ONE ISSUE
# ============================================================

def _normalize_issue(issue):
    """
    Normalize one LLM-generated semantic issue.

    Removes unexpected fields and guarantees the structure
    expected by the rest of the application.
    """

    if not isinstance(issue, dict):
        return None

    category = str(
        issue.get("category", "other")
    ).strip().lower()

    severity = str(
        issue.get("severity", "MEDIUM")
    ).strip().upper()

    confidence = str(
        issue.get("confidence", "MEDIUM")
    ).strip().upper()

    allowed_categories = {
        "bug",
        "security",
        "performance",
        "edge_case",
        "concurrency",
        "resource",
        "database",
        "maintainability",
        "testing",
        "other",
    }

    allowed_severities = {
        "CRITICAL",
        "HIGH",
        "MEDIUM",
        "LOW",
    }

    allowed_confidence = {
        "HIGH",
        "MEDIUM",
        "LOW",
    }

    if category not in allowed_categories:
        category = "other"

    if severity not in allowed_severities:
        severity = "MEDIUM"

    if confidence not in allowed_confidence:
        confidence = "MEDIUM"

    return {
        "category": category,
        "severity": severity,
        "confidence": confidence,
        "line": issue.get("line"),
        "end_line": issue.get("end_line"),
        "problem": str(
            issue.get("problem", "")
        ).strip(),
        "evidence": str(
            issue.get("evidence", "")
        ).strip(),
        "why": str(
            issue.get("why", "")
        ).strip(),
        "verification": str(
            issue.get("verification", "")
        ).strip(),
        "change": str(
            issue.get("change", "")
        ).strip(),
    }


# ============================================================
# VALIDATE ISSUE
# ============================================================

def _is_valid_issue(issue):
    """
    Basic validation for an LLM-generated issue.

    This does not prove that the issue is correct.
    It only prevents malformed findings from entering the
    application.
    """

    if not isinstance(issue, dict):
        return False

    required_fields = {
        "category",
        "severity",
        "confidence",
        "line",
        "end_line",
        "problem",
        "evidence",
        "why",
        "verification",
        "change",
    }

    if set(issue.keys()) != required_fields:
        return False

    if not issue["problem"]:
        return False

    if not issue["evidence"]:
        return False

    if not issue["why"]:
        return False

    if not issue["verification"]:
        return False

    if not issue["change"]:
        return False

    return True


# ============================================================
# SEMANTIC CODE REVIEW
# ============================================================

def review_code_semantically(source_code: str):
    """
    Ask the local Ollama model for a broad semantic code review.

    Static analysis:
        Ruff
        Bandit

    Semantic analysis:
        Ollama / Qwen

    The semantic reviewer focuses on issues that require
    understanding the code rather than simple pattern matching.
    """

    print(
        "\n========== SEMANTIC REVIEW REQUEST =========="
    )

    print(
        f"Model: {MODEL_NAME}"
    )

    print(
        f"Source length: {len(source_code)} characters"
    )

    # --------------------------------------------------------
    # Build prompt
    # --------------------------------------------------------

    prompt = build_semantic_review_prompt(
        source_code
    )

    print(
        f"Prompt length: {len(prompt)} characters"
    )

    # --------------------------------------------------------
    # Start timer
    # --------------------------------------------------------

    start_time = time.perf_counter()

    try:

        print(
            "\n========== SENDING REQUEST TO OLLAMA =========="
        )

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
            timeout=180,
        )

        elapsed = (
            time.perf_counter()
            - start_time
        )

        print(
            f"\nOllama response received in "
            f"{elapsed:.2f} seconds."
        )

        # ----------------------------------------------------
        # HTTP validation
        # ----------------------------------------------------

        response.raise_for_status()

        # ----------------------------------------------------
        # Parse Ollama response
        # ----------------------------------------------------

        data = response.json()

        ai_response = data.get(
            "response",
            "",
        )

        if not isinstance(
            ai_response,
            str,
        ):

            print(
                "\n⚠️ Ollama response field is invalid."
            )

            return {
                "issues": [],
                "error": (
                    "Ollama returned an invalid response field."
                ),
            }

        ai_response = ai_response.strip()

        if not ai_response:

            print(
                "\n⚠️ Semantic review returned "
                "an empty response."
            )

            return {
                "issues": [],
                "error": (
                    "Ollama returned an empty "
                    "semantic review response."
                ),
            }

        print(
            "\n========== RAW SEMANTIC RESPONSE =========="
        )

        print(
            ai_response
        )

        # ----------------------------------------------------
        # Parse JSON
        # ----------------------------------------------------

        parsed = parse_ai_json(
            ai_response
        )

        if parsed is None:

            print(
                "\n⚠️ Ollama returned invalid JSON."
            )

            return {
                "issues": [],
                "error": (
                    "Ollama returned invalid JSON."
                ),
            }

        # ----------------------------------------------------
        # Validate top-level response
        # ----------------------------------------------------

        if not isinstance(
            parsed,
            dict,
        ):

            return {
                "issues": [],
                "error": (
                    "Semantic review response "
                    "must be a JSON object."
                ),
            }

        issues = parsed.get(
            "issues",
            [],
        )

        if not isinstance(
            issues,
            list,
        ):

            print(
                "\n⚠️ Semantic review issues "
                "field is not a list."
            )

            return {
                "issues": [],
                "error": (
                    "Semantic review returned "
                    "an invalid issues format."
                ),
            }

        # ----------------------------------------------------
        # Normalize and validate issues
        # ----------------------------------------------------

        normalized_issues = []

        for issue in issues:

            normalized = _normalize_issue(
                issue
            )

            if normalized is None:
                continue

            if not _is_valid_issue(
                normalized
            ):

                print(
                    "\n⚠️ Ignoring malformed "
                    "semantic issue:"
                )

                print(
                    normalized
                )

                continue

            normalized_issues.append(
                normalized
            )

        # ----------------------------------------------------
        # Final result
        # ----------------------------------------------------

        print(
            "\n========== SEMANTIC REVIEW COMPLETE =========="
        )

        print(
            f"Issues detected: "
            f"{len(normalized_issues)}"
        )

        return {
            "issues": normalized_issues,
        }

    # ========================================================
    # TIMEOUT
    # ========================================================

    except requests.exceptions.Timeout:

        elapsed = (
            time.perf_counter()
            - start_time
        )

        print(
            f"\n⚠️ Semantic review request "
            f"timed out after {elapsed:.2f} seconds."
        )

        return {
            "issues": [],
            "error": (
                "Semantic review request timed out."
            ),
        }

    # ========================================================
    # OLLAMA CONNECTION ERROR
    # ========================================================

    except requests.exceptions.ConnectionError:

        elapsed = (
            time.perf_counter()
            - start_time
        )

        print(
            f"\n⚠️ Could not connect to Ollama "
            f"after {elapsed:.2f} seconds."
        )

        return {
            "issues": [],
            "error": (
                "Could not connect to Ollama. "
                "Make sure Ollama is running."
            ),
        }

    # ========================================================
    # HTTP / REQUEST ERROR
    # ========================================================

    except requests.exceptions.RequestException as e:

        elapsed = (
            time.perf_counter()
            - start_time
        )

        print(
            f"\n⚠️ Semantic review request failed "
            f"after {elapsed:.2f} seconds."
        )

        print(
            f"Error: {e}"
        )

        return {
            "issues": [],
            "error": (
                "Semantic review request failed."
            ),
        }

    # ========================================================
    # JSON ERROR
    # ========================================================

    except ValueError as e:

        print(
            f"\n⚠️ Failed to parse Ollama response: {e}"
        )

        return {
            "issues": [],
            "error": (
                "Failed to parse Ollama response."
            ),
        }

    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as e:

        elapsed = (
            time.perf_counter()
            - start_time
        )

        print(
            f"\n⚠️ Unexpected semantic review "
            f"error after {elapsed:.2f} seconds."
        )

        print(
            f"Error: {e}"
        )

        return {
            "issues": [],
            "error": (
                "Unexpected semantic review error."
            ),
        }