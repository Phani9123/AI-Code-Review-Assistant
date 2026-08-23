from backend.app.services.finding_validation_service import (
    validate_and_deduplicate_findings,
)


# ============================================================
# TEST SOURCE
# ============================================================

SOURCE_CODE = """def authenticate(username, password, users):
    if username in users and password:
        return True

    return False
"""


# ============================================================
# TEST FINDINGS
# ============================================================

findings = [
    {
        "source": "semantic",
        "category": "security",
        "severity": "HIGH",
        "confidence": "HIGH",
        "line": 2,
        "end_line": 2,
        "problem": "Insecure password check",
        "evidence": "if password:",
        "why": (
            "The password is checked only for truthiness "
            "instead of being verified."
        ),
        "verification": (
            "Provide an incorrect non-empty password "
            "and observe that authentication succeeds."
        ),
        "change": (
            "Compare the supplied password with the "
            "stored credential."
        ),
    },

    # --------------------------------------------------------
    # Intentional duplicate
    # --------------------------------------------------------

    {
        "source": "semantic",
        "category": "security",
        "severity": "HIGH",
        "confidence": "HIGH",
        "line": 2,
        "end_line": 2,
        "problem": "Insecure password check",
        "evidence": "if password:",
        "why": (
            "The code accepts any non-empty password."
        ),
        "verification": (
            "Use a wrong non-empty password."
        ),
        "change": (
            "Verify the password against the stored "
            "credential."
        ),
    },

    # --------------------------------------------------------
    # Valid Ruff-style finding
    # --------------------------------------------------------

    {
        "source": "ruff",
        "category": "style",
        "severity": "LOW",
        "confidence": "HIGH",
        "line": 2,
        "end_line": 5,
        "problem": (
            "Return the condition directly"
        ),
        "evidence": (
            "if username in users and password:"
        ),
        "why": "",
        "verification": "",
        "change": (
            "Return the boolean condition directly."
        ),
    },

    # --------------------------------------------------------
    # Invalid semantic finding
    #
    # Evidence does NOT exist in line 2.
    # --------------------------------------------------------

    {
        "source": "semantic",
        "category": "security",
        "severity": "HIGH",
        "confidence": "HIGH",
        "line": 2,
        "end_line": 2,
        "problem": "SQL injection",
        "evidence": "SELECT * FROM users",
        "why": (
            "User input is directly inserted into SQL."
        ),
        "verification": (
            "Provide malicious SQL input."
        ),
        "change": (
            "Use parameterized SQL queries."
        ),
    },
]


# ============================================================
# RUN VALIDATION
# ============================================================

print(
    "========== FINDING VALIDATION TEST =========="
)


result = validate_and_deduplicate_findings(
    findings,
    SOURCE_CODE,
    filename="backend/app/vulnerable_test.py",
)


# ============================================================
# PRINT RESULTS
# ============================================================

print(
    "\n========== VALIDATION RESULT =========="
)

print(
    f"Before validation: {len(findings)}"
)

print(
    f"After validation: "
    f"{result['before_deduplication']}"
)

print(
    f"After deduplication: "
    f"{result['after_deduplication']}"
)

print(
    f"Duplicates removed: "
    f"{result['duplicates_removed']}"
)

print(
    f"Rejected findings: "
    f"{len(result['rejected'])}"
)


print(
    "\n========== FINAL FINDINGS =========="
)

for index, finding in enumerate(
    result["findings"],
    start=1,
):

    print(
        f"\nFinding #{index}"
    )

    print(
        f"Source: "
        f"{finding.get('source')}"
    )

    print(
        f"Severity: "
        f"{finding.get('severity')}"
    )

    print(
        f"Category: "
        f"{finding.get('category')}"
    )

    print(
        f"Line: "
        f"{finding.get('line')}"
    )

    print(
        f"Problem: "
        f"{finding.get('problem')}"
    )