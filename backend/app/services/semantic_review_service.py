import json
import time

import requests

from backend.app.services.ollama_service import (
    OLLAMA_URL,
    MODEL_NAME,
)


# ============================================================
# CONFIGURATION
# ============================================================

MAX_SEMANTIC_INPUT = 12000


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

The input is a Git Pull Request patch containing added
lines and their REAL NEW-FILE LINE NUMBERS.

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
14. Keep every field concise.
15. Keep problem, evidence, why, verification, and change to
    one or two sentences.
16. Never stop before completing valid JSON.
17. The line field MUST refer to the REAL SOURCE FILE LINE NUMBER
    shown in the LINE prefix.
18. Evidence MUST match the code on that source line.
19. Do not report findings for context lines that are not added
    lines.

Return ONLY valid JSON.

Required structure:

{{
  "issues": [
    {{
      "category": "security",
      "severity": "HIGH",
      "confidence": "HIGH",
      "line": 13,
      "end_line": 13,
      "problem": "Short description",
      "evidence": "Exact changed code",
      "why": "Why this is a real problem",
      "verification": "How to demonstrate the problem",
      "change": "Specific fix"
    }}
  ]
}}

Categories:

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

Severity:

CRITICAL
HIGH
MEDIUM
LOW

Confidence:

HIGH
MEDIUM
LOW

Important examples:

Authentication:

    LINE 4: if username in users and password:
    LINE 5:     return True

Report that a non-empty password is accepted without
comparing it with the stored password.

SQL injection:

    LINE 13: query = f"SELECT * FROM users WHERE username = '{{username}}'"

Report SQL injection ONLY when the changed code demonstrates
that user-controlled data reaches the SQL query.

Mutable default:

    LINE 10: def add_item(item, items=[]):

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
    Extract added lines from a Git patch while preserving
    their actual line numbers in the new file.

    Example Git hunk:

        @@ -7,4 +7,16 @@
         existing line
        +new line

    becomes:

        LINE 8: new line

    This allows the semantic reviewer to report the real
    source-code line number instead of a relative patch line.

    If normal source code is provided instead of a Git patch,
    return it unchanged.
    """

    if not patch:
        return ""

    lines = patch.splitlines()

    # --------------------------------------------------------
    # Detect Git diff
    # --------------------------------------------------------

    is_git_diff = any(
        line.startswith("@@")
        for line in lines
    )

    # --------------------------------------------------------
    # Normal source code
    # --------------------------------------------------------

    if not is_git_diff:
        return patch.strip()

    # --------------------------------------------------------
    # Parse Git diff
    # --------------------------------------------------------

    changed_lines = []

    current_new_line = None

    for line in lines:

        # ----------------------------------------------------
        # Hunk header
        #
        # Example:
        #
        # @@ -7,4 +7,16 @@
        # ----------------------------------------------------

        if line.startswith("@@"):

            try:
                plus_part = line.split("+", 1)[1]
                new_range = plus_part.split(" ", 1)[0]

                new_start = new_range.split(",", 1)[0]

                current_new_line = int(
                    new_start
                )

            except (
                ValueError,
                IndexError,
            ):
                current_new_line = None

            continue

        # ----------------------------------------------------
        # Ignore diff metadata
        # ----------------------------------------------------

        if line.startswith(
            (
                "diff ",
                "index ",
                "---",
                "+++",
                "\\ No newline",
            )
        ):
            continue

        # ----------------------------------------------------
        # Added line
        # ----------------------------------------------------

        if line.startswith("+"):

            if current_new_line is not None:

                code = line[1:]

                changed_lines.append(
                    f"LINE {current_new_line}: {code}"
                )

                current_new_line += 1

            continue

        # ----------------------------------------------------
        # Deleted line
        #
        # Deleted lines do not exist in the new file,
        # therefore they do not increment the new-file
        # line number.
        # ----------------------------------------------------

        if line.startswith("-"):

            continue

        # ----------------------------------------------------
        # Context line
        #
        # Context exists in both old and new files, so it
        # advances the new-file line number.
        # ----------------------------------------------------

        if current_new_line is not None:

            current_new_line += 1

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
            len(line) + 1
        )

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

        current_length += line_length

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
    Normalize one model-generated issue.

    Returns None when the structure is invalid.
    """

    if not isinstance(
        issue,
        dict,
    ):
        return None

    try:

        line = int(
            issue.get(
                "line"
            )
        )

        end_line = int(
            issue.get(
                "end_line",
                line,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return None

    category = str(
        issue.get(
            "category",
            "other",
        )
    ).upper()

    severity = str(
        issue.get(
            "severity",
            "MEDIUM",
        )
    ).upper()

    confidence = str(
        issue.get(
            "confidence",
            "MEDIUM",
        )
    ).upper()

    return {
        "category": category.lower(),
        "severity": severity,
        "confidence": confidence,
        "line": line,
        "end_line": end_line,
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
# VALIDATE ONE ISSUE
# ============================================================

def _is_valid_issue(
    issue,
) -> bool:
    """
    Validate the normalized semantic issue structure.
    """

    if not isinstance(
        issue,
        dict,
    ):
        return False

    required_fields = [
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
    ]

    for field in required_fields:

        if field not in issue:
            return False

    if not isinstance(
        issue["line"],
        int,
    ):
        return False

    if not isinstance(
        issue["end_line"],
        int,
    ):
        return False

    if issue["line"] < 1:
        return False

    if issue["end_line"] < issue["line"]:
        return False

    if not issue["problem"]:
        return False

    if not issue["evidence"]:
        return False

    return True


# ============================================================
# PARSE OLLAMA JSON
# ============================================================

def _parse_ollama_response(
    response_text: str,
):
    """
    Parse JSON returned by Ollama.

    The model is instructed to return JSON only, but this
    function also handles common markdown-fenced responses.
    """

    if not response_text:
        return {
            "issues": []
        }

    text = response_text.strip()

    # --------------------------------------------------------
    # Remove markdown code fences if the model added them.
    # --------------------------------------------------------

    if text.startswith(
        "```"
    ):

        lines = text.splitlines()

        if lines:

            lines = lines[1:]

        if lines and lines[-1].strip() == "```":

            lines = lines[:-1]

        text = "\n".join(
            lines
        ).strip()

    # --------------------------------------------------------
    # Parse JSON
    # --------------------------------------------------------

    data = json.loads(
        text
    )

    if not isinstance(
        data,
        dict,
    ):

        return {
            "issues": []
        }

    issues = data.get(
        "issues",
        [],
    )

    if not isinstance(
        issues,
        list,
    ):

        issues = []

    return {
        "issues": issues
    }


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

    Returns a list of raw issues.
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

    print(
        "\n========== SENDING REQUEST TO OLLAMA =========="
    )

    start_time = time.perf_counter()

    try:

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=180,
        )

        elapsed = (
            time.perf_counter()
            - start_time
        )

        response.raise_for_status()

        print(
            f"\nOllama response received "
            f"in {elapsed:.2f} seconds."
        )

        response_data = response.json()

        response_text = response_data.get(
            "response",
            "",
        )

        print(
            "\n========== RAW SEMANTIC RESPONSE =========="
        )

        print(
            response_text
        )

        parsed = _parse_ollama_response(
            response_text
        )

        return parsed.get(
            "issues",
            [],
        )

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

    except ValueError as error:

        print(
            f"\nFailed to parse Ollama response: "
            f"{error}"
        )

        return []

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
        Pull Request patch.

    Pipeline:
        PR patch
        -> Extract changed lines
        -> Split large input
        -> Ollama / Qwen
        -> Parse JSON
        -> Normalize findings
        -> Validate structure
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