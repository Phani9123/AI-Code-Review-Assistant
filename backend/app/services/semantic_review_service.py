import time

import requests

from backend.app.services.ollama_service import (
    MODEL_NAME,
    OLLAMA_URL,
    parse_ai_json,
)


# ============================================================
# SEMANTIC REVIEW CONFIGURATION
# ============================================================

MAX_SEMANTIC_INPUT = 8000
MAX_SEMANTIC_OUTPUT = 150
SEMANTIC_TIMEOUT = 90


# ============================================================
# SEMANTIC REVIEW PROMPT
# ============================================================

def build_semantic_review_prompt(
    source_code: str,
) -> str:
    """
    Build a focused semantic-review prompt for Pull Request
    changes.

    Ruff and Bandit handle deterministic/static findings.
    Ollama focuses on behavioral problems that require
    semantic reasoning.
    """

    return f"""
You are a senior Python security and code reviewer.

Review ONLY the changed code provided below.

The input may be a Git diff/patch containing added lines
and minimal surrounding context.

Your job is to find REAL problems that require semantic
reasoning and may be missed by Ruff or Bandit.

Focus on:

- logic bugs
- authentication bugs
- authorization bugs
- security vulnerabilities
- incorrect data flow
- runtime errors caused by the changes
- important edge cases
- race conditions
- resource leaks
- database/API misuse
- serious performance problems

DO NOT report:

- formatting
- import ordering
- unused imports
- naming style
- return simplification
- Ruff-style issues
- generic maintainability preferences
- hypothetical vulnerabilities
- problems in unchanged code
- hardcoded values unless they are actually sensitive
- SQL injection unless user-controlled data reaches SQL
- authentication problems unless the execution path
  demonstrates them

RULES:

1. Report ONLY real problems demonstrated by the changed code.
2. Do not invent requirements or business logic.
3. Do not speculate about unseen code.
4. Do not report deleted code.
5. Evidence must come directly from the provided changes.
6. Use the smallest relevant line range.
7. Keep findings concise.
8. Prefer zero findings over speculative findings.
9. If evidence does not clearly prove the issue, do not report it.
10. Do not report a vulnerability merely because a dangerous
    API or function exists. Show how the changed code makes
    the vulnerable behavior possible.
11. Do not invent function arguments, variables, values, or
    execution paths.
12. For security findings, explain the actual attacker-controlled
    or externally-controlled data flow when it is visible.
13. Prefer HIGH confidence findings supported by exact evidence.
14. Keep every field concise. Do not write long explanations.
15. Keep problem, evidence, why, verification, and change to one or two sentences.
16. Never stop before completing valid JSON.

Return ONLY valid JSON.

Required structure:

{{
  "issues": [
    {{
      "category": "security",
      "severity": "HIGH",
      "confidence": "HIGH",
      "line": 1,
      "end_line": 1,
      "problem": "Short description",
      "evidence": "Exact changed code",
      "why": "Why this is a real problem",
      "verification": "How to demonstrate the problem",
      "change": "Specific fix"
    }}
  ]
}}

Categories:
bug, security, performance, edge_case, concurrency,
resource, database, maintainability, testing, other

Severity:
CRITICAL, HIGH, MEDIUM, LOW

Confidence:
HIGH, MEDIUM, LOW

Important examples:

Authentication:

    if username in users and password:
        return True

Report that a non-empty password is accepted without
comparing it with the stored password.

SQL injection:

    query = f"SELECT * FROM users WHERE username = '{{username}}'"

Report SQL injection ONLY when the changed code demonstrates
that user-controlled data reaches the SQL query.

Mutable default:

    def add_item(item, items=[]):

Report the shared mutable default argument if the changed
code introduces or modifies it.

If there are no real issues, return:

{{
  "issues": []
}}

CHANGED CODE:

{source_code}
"""


# ============================================================
# EXTRACT CHANGED LINES
# ============================================================

def extract_changed_lines(
    patch: str,
) -> str:
    """
    Extract changed lines from a Git patch.

    If the input is a Git diff, keep hunk headers and added
    lines while excluding deleted lines.

    If the input is normal source code rather than a Git diff,
    return the source unchanged so direct testing still works.
    """

    if not patch:
        return ""

    lines = patch.splitlines()

    # --------------------------------------------------------
    # Detect whether the input is actually a Git diff.
    # --------------------------------------------------------

    is_git_diff = any(
        line.startswith("@@")
        for line in lines
    )

    # --------------------------------------------------------
    # Normal Python source.
    #
    # This is important for direct testing.
    # --------------------------------------------------------

    if not is_git_diff:
        return patch.strip()

    # --------------------------------------------------------
    # Git diff.
    # Keep:
    #   @@ hunk headers
    #   + added lines
    #
    # Exclude:
    #   - deleted lines
    #   +++ file headers
    # --------------------------------------------------------

    changed_lines = []

    for line in lines:

        if line.startswith("@@"):
            changed_lines.append(line)
            continue

        if (
            line.startswith("+")
            and not line.startswith("+++")
        ):
            changed_lines.append(line)

    return "\n".join(
        changed_lines
    )


# ============================================================
# SPLIT LARGE SEMANTIC INPUT
# ============================================================

def split_semantic_input(
    source_code: str,
    max_size: int = MAX_SEMANTIC_INPUT,
) -> list:
    """
    Split large semantic-review input into manageable chunks.

    This prevents very large PR patches from creating huge
    Ollama prompts and excessive inference time.
    """

    if not source_code:
        return []

    if len(source_code) <= max_size:
        return [
            source_code
        ]

    chunks = []

    current_lines = []
    current_length = 0

    for line in source_code.splitlines():

        line_length = (
            len(line)
            + 1
        )

        # ----------------------------------------------------
        # Start a new chunk when the current chunk reaches
        # the configured maximum size.
        # ----------------------------------------------------

        if (
            current_lines
            and
            current_length + line_length
            > max_size
        ):

            chunks.append(
                "\n".join(
                    current_lines
                )
            )

            current_lines = []
            current_length = 0

        current_lines.append(
            line
        )

        current_length += (
            line_length
        )

    # --------------------------------------------------------
    # Add final chunk.
    # --------------------------------------------------------

    if current_lines:

        chunks.append(
            "\n".join(
                current_lines
            )
        )

    return chunks


# ============================================================
# NORMALIZE ONE ISSUE
# ============================================================

def _normalize_issue(
    issue,
):
    """
    Normalize one LLM-generated semantic issue.

    Removes unexpected fields and guarantees the structure
    expected by the rest of the application.
    """

    if not isinstance(
        issue,
        dict,
    ):
        return None

    category = str(
        issue.get(
            "category",
            "other",
        )
    ).strip().lower()

    severity = str(
        issue.get(
            "severity",
            "MEDIUM",
        )
    ).strip().upper()

    confidence = str(
        issue.get(
            "confidence",
            "MEDIUM",
        )
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

        "line": issue.get(
            "line"
        ),

        "end_line": issue.get(
            "end_line"
        ),

        "problem": str(
            issue.get(
                "problem",
                "",
            )
        ).strip(),

        "evidence": str(
            issue.get(
                "evidence",
                "",
            )
        ).strip(),

        "why": str(
            issue.get(
                "why",
                "",
            )
        ).strip(),

        "verification": str(
            issue.get(
                "verification",
                "",
            )
        ).strip(),

        "change": str(
            issue.get(
                "change",
                "",
            )
        ).strip(),
    }


# ============================================================
# VALIDATE ISSUE
# ============================================================

def _is_valid_issue(
    issue,
):
    """
    Basic validation for an LLM-generated issue.

    This does not prove that the issue is correct.
    It prevents malformed findings from entering the
    application.
    """

    if not isinstance(
        issue,
        dict,
    ):
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

    if set(
        issue.keys()
    ) != required_fields:
        return False

    if not issue[
        "problem"
    ]:
        return False

    if not issue[
        "evidence"
    ]:
        return False

    if not issue[
        "why"
    ]:
        return False

    if not issue[
        "verification"
    ]:
        return False

    if not issue[
        "change"
    ]:
        return False

    return True


# ============================================================
# REVIEW ONE SEMANTIC CHUNK
# ============================================================

def _review_semantic_chunk(
    chunk: str,
    chunk_number: int,
    total_chunks: int,
):
    """
    Send one semantic-review chunk to Ollama.

    Returns:
        list of raw issues
    """

    print(
        "\n========== SEMANTIC CHUNK "
        f"{chunk_number}/{total_chunks} =========="
    )

    print(
        f"Chunk length: "
        f"{len(chunk)} characters"
    )

    prompt = build_semantic_review_prompt(
        chunk
    )

    print(
        f"Prompt length: "
        f"{len(prompt)} characters"
    )

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
                    "num_predict": 400,
                },
            },
            timeout=120,
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
        # Parse HTTP JSON
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
                "\nOllama response field is invalid."
            )

            return []

        ai_response = ai_response.strip()

        if not ai_response:

            print(
                "\nSemantic review returned "
                "an empty response."
            )

            return []

        print(
            "\n========== RAW SEMANTIC RESPONSE =========="
        )

        print(
            ai_response
        )

        # ----------------------------------------------------
        # Parse AI JSON
        # ----------------------------------------------------

        parsed = parse_ai_json(
            ai_response
        )

        if parsed is None:

            print(
                "\nOllama returned invalid JSON."
            )

            return []

        # ----------------------------------------------------
        # Validate top-level response
        # ----------------------------------------------------

        if not isinstance(
            parsed,
            dict,
        ):

            print(
                "\nSemantic review response "
                "must be a JSON object."
            )

            return []

        issues = parsed.get(
            "issues",
            [],
        )

        if not isinstance(
            issues,
            list,
        ):

            print(
                "\nSemantic review issues "
                "field is not a list."
            )

            return []

        return issues

    # ========================================================
    # TIMEOUT
    # ========================================================

    except requests.exceptions.Timeout:

        elapsed = (
            time.perf_counter()
            - start_time
        )

        print(
            f"\nSemantic review chunk "
            f"{chunk_number} timed out after "
            f"{elapsed:.2f} seconds."
        )

        print(
            "Skipping this chunk."
        )

        return []

    # ========================================================
    # OLLAMA CONNECTION ERROR
    # ========================================================

    except requests.exceptions.ConnectionError:

        elapsed = (
            time.perf_counter()
            - start_time
        )

        print(
            f"\nCould not connect to Ollama "
            f"after {elapsed:.2f} seconds."
        )

        print(
            "Skipping this chunk."
        )

        return []

    # ========================================================
    # HTTP / REQUEST ERROR
    # ========================================================

    except requests.exceptions.RequestException as error:

        elapsed = (
            time.perf_counter()
            - start_time
        )

        print(
            f"\nSemantic review request failed "
            f"after {elapsed:.2f} seconds."
        )

        print(
            f"Error: {error}"
        )

        print(
            "Skipping this chunk."
        )

        return []

    # ========================================================
    # JSON / VALUE ERROR
    # ========================================================

    except ValueError as error:

        print(
            f"\nFailed to parse Ollama response: "
            f"{error}"
        )

        return []

    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as error:

        print(
            "\nUnexpected semantic review "
            "error:"
        )

        print(
            f"Error: {error}"
        )

        return []


# ============================================================
# SEMANTIC CODE REVIEW
# ============================================================

def review_code_semantically(
    source_code: str,
):
    """
    Ask the local Ollama model for a semantic code review.

    Input:
        - Pull Request patch
        - complete source file as fallback

    Pipeline:

        PR patch
            ↓
        Extract changed lines
            ↓
        Split large input
            ↓
        Ollama / Qwen
            ↓
        Parse JSON
            ↓
        Normalize findings
            ↓
        Validate structure
    """

    print(
        "\n========== SEMANTIC REVIEW REQUEST =========="
    )

    print(
        f"Model: {MODEL_NAME}"
    )

    print(
        f"Original input length: "
        f"{len(source_code)} characters"
    )

    # ========================================================
    # EXTRACT CHANGED CODE
    # ========================================================

    semantic_input = extract_changed_lines(
        source_code
    )

    if not semantic_input:

        print(
            "\nNo added lines found for semantic review."
        )

        return {
            "issues": [],
        }

    print(
        f"\nChanged semantic input length: "
        f"{len(semantic_input)} characters"
    )

    print(
        "\n========== SEMANTIC REVIEW INPUT =========="
    )

    print(
        semantic_input
    )

    # ========================================================
    # SPLIT LARGE INPUT
    # ========================================================

    chunks = split_semantic_input(
        semantic_input
    )

    if not chunks:

        print(
            "\nNo semantic-review chunks generated."
        )

        return {
            "issues": [],
        }

    print(
        f"\nSemantic review chunks: "
        f"{len(chunks)}"
    )

    # ========================================================
    # REVIEW ALL CHUNKS
    # ========================================================

    all_issues = []

    for chunk_number, chunk in enumerate(
        chunks,
        start=1,
    ):

        issues = _review_semantic_chunk(
            chunk,
            chunk_number,
            len(chunks),
        )

        if issues:

            all_issues.extend(
                issues
            )

    # ========================================================
    # NORMALIZE + VALIDATE
    # ========================================================

    normalized_issues = []

    for issue in all_issues:

        normalized = _normalize_issue(
            issue
        )

        if normalized is None:

            print(
                "\nIgnoring invalid semantic issue."
            )

            continue

        if not _is_valid_issue(
            normalized
        ):

            print(
                "\nIgnoring malformed "
                "semantic issue:"
            )

            print(
                normalized
            )

            continue

        normalized_issues.append(
            normalized
        )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print(
        "\n========== SEMANTIC REVIEW COMPLETE =========="
    )

    print(
        f"Raw issues received: "
        f"{len(all_issues)}"
    )

    print(
        f"Valid issues detected: "
        f"{len(normalized_issues)}"
    )

    return {
        "issues": normalized_issues,
    }