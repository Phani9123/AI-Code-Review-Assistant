from backend.app.services.review_report_service import (
    build_review_report,
)


# ============================================================
# TEST FINDINGS
# ============================================================

findings = [
    {
        "filename": "backend/app/vulnerable_test.py",
        "source": "semantic",
        "category": "security",
        "severity": "HIGH",
        "confidence": "HIGH",
        "line": 2,
        "end_line": 2,
        "problem": "Insecure password check",
        "evidence": "if username in users and password:",
        "why": (
            "A non-empty password is accepted "
            "without comparing it with the stored password."
        ),
        "fix": (
            "Compare the supplied password with "
            "the stored credential."
        ),
    },
    {
        "filename": "backend/app/vulnerable_test.py",
        "source": "ruff",
        "category": "style",
        "severity": "LOW",
        "confidence": "HIGH",
        "line": 2,
        "end_line": 5,
        "problem": (
            "Return the condition directly"
        ),
        "evidence": "",
        "why": "",
        "fix": (
            "Return the boolean condition directly."
        ),
    },
]


# ============================================================
# BUILD REPORT
# ============================================================

print(
    "========== REVIEW REPORT TEST =========="
)


result = build_review_report(
    findings=findings,
    files_analyzed=1,
    files_skipped=0,
)


# ============================================================
# PRINT STRUCTURED RESULT
# ============================================================

print(
    "\n========== STRUCTURED REPORT =========="
)

print(
    f"Status: {result['status']}"
)

print(
    f"Files analyzed: "
    f"{result['files_analyzed']}"
)

print(
    f"Files skipped: "
    f"{result['files_skipped']}"
)

print(
    f"Total findings: "
    f"{result['total_findings']}"
)

print(
    f"Severity counts: "
    f"{result['severity_counts']}"
)

print(
    f"Category counts: "
    f"{result['category_counts']}"
)

print(
    f"Source counts: "
    f"{result['source_counts']}"
)


# ============================================================
# PRINT MARKDOWN
# ============================================================

print(
    "\n========== MARKDOWN REPORT =========="
)

print(
    result["markdown"]
)