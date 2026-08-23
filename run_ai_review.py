from backend.app.services.pr_review_service import (
    review_pull_request,
)

from backend.app.services.review_report_service import (
    build_review_report,
)

from backend.app.services.github_review_service import (
    post_pull_request_review,
)


# ============================================================
# CONFIGURATION
# ============================================================

REPOSITORY = (
    "Phani9123/AI-Code-Review-Assistant"
)

PR_NUMBER = 1


# ============================================================
# START
# ============================================================

print(
    "=================================================="
)

print(
    "AI CODE REVIEW ASSISTANT"
)

print(
    "=================================================="
)

print(
    f"Repository: {REPOSITORY}"
)

print(
    f"Pull Request: #{PR_NUMBER}"
)


# ============================================================
# STEP 1 — REVIEW PULL REQUEST
# ============================================================

print(
    "\n========== RUNNING PR ANALYSIS =========="
)

review_result = review_pull_request(
    REPOSITORY,
    PR_NUMBER,
)


# ============================================================
# STEP 2 — GET FINDINGS
# ============================================================

findings = review_result.get(
    "findings",
    [],
)

files_analyzed = review_result.get(
    "files_analyzed",
    0,
)

files_skipped = review_result.get(
    "files_skipped",
    0,
)


print(
    "\n========== ANALYSIS COMPLETE =========="
)

print(
    f"Files analyzed: {files_analyzed}"
)

print(
    f"Files skipped: {files_skipped}"
)

print(
    f"Findings: {len(findings)}"
)


# ============================================================
# STEP 3 — GENERATE REVIEW REPORT
# ============================================================

print(
    "\n========== GENERATING REVIEW REPORT =========="
)

report = build_review_report(
    findings=findings,
    files_analyzed=files_analyzed,
    files_skipped=files_skipped,
)


status = report.get(
    "status",
    "APPROVED",
)

markdown = report.get(
    "markdown",
    "",
)


print(
    f"Review status: {status}"
)

print(
    f"Total findings: "
    f"{report.get('total_findings', 0)}"
)


# ============================================================
# STEP 4 — DISPLAY REPORT
# ============================================================

print(
    "\n========== GENERATED REPORT =========="
)

print(
    markdown
)


# ============================================================
# STEP 5 — POST TO GITHUB
# ============================================================

print(
    "\n========== POSTING REVIEW TO GITHUB =========="
)

github_result = post_pull_request_review(
    repository_name=REPOSITORY,
    pull_request_number=PR_NUMBER,
    review_body=markdown,
    status=status,
)


# ============================================================
# STEP 6 — FINAL RESULT
# ============================================================

print(
    "\n=================================================="
)

print(
    "AI CODE REVIEW COMPLETE"
)

print(
    "=================================================="
)

print(
    f"Status: {status}"
)

print(
    f"GitHub event: "
    f"{github_result.get('event')}"
)

print(
    f"Review ID: "
    f"{github_result.get('review_id')}"
)

print(
    f"Review URL: "
    f"{github_result.get('review_url')}"
)