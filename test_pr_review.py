from backend.app.services.pr_review_service import (
    review_pull_request,
)


# ============================================================
# CONFIGURATION
# ============================================================

REPOSITORY = (
    "Phani9123/AI-Code-Review-Assistant"
)

PR_NUMBER = 1


# ============================================================
# RUN PR REVIEW
# ============================================================

print(
    "========== COMPLETE PR REVIEW TEST =========="
)


result = review_pull_request(
    REPOSITORY,
    PR_NUMBER,
)


# ============================================================
# DISPLAY FINAL FINDINGS
# ============================================================

print(
    "\n\n========== FINAL PR FINDINGS =========="
)


for index, finding in enumerate(
    result.get(
        "findings",
        [],
    ),
    start=1,
):

    print(
        f"\nFinding #{index}"
    )

    print(
        f"File: "
        f"{finding.get('filename')}"
    )

    print(
        f"Source: "
        f"{finding.get('source')}"
    )

    print(
        f"Category: "
        f"{finding.get('category')}"
    )

    print(
        f"Severity: "
        f"{finding.get('severity')}"
    )

    print(
        f"Confidence: "
        f"{finding.get('confidence')}"
    )

    print(
        f"Line: "
        f"{finding.get('line')}"
    )

    print(
        f"Problem: "
        f"{finding.get('problem')}"
    )

    print(
        f"Why: "
        f"{finding.get('why')}"
    )

    print(
        f"Fix: "
        f"{finding.get('fix')}"
    )


# ============================================================
# SUMMARY
# ============================================================

print(
    "\n\n========== REVIEW SUMMARY =========="
)

print(
    f"Files analyzed: "
    f"{result.get('files_analyzed')}"
)

print(
    f"Files skipped: "
    f"{result.get('files_skipped')}"
)

print(
    f"Total findings: "
    f"{result.get('total_findings')}"
)
# ============================================================
# REVIEW REPORT
# ============================================================

print(
    "\n\n========== GENERATED REVIEW REPORT =========="
)

print(
    result.get(
        "markdown_report",
        "No review report generated.",
    )
)