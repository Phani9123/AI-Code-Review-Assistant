from backend.app.services.github_service import (
    get_pull_request_file_content,
)

from backend.app.services.semantic_review_service import (
    review_code_semantically,
)


REPOSITORY = "Phani9123/AI-Code-Review-Assistant"
PR_NUMBER = 1
FILE_PATH = "backend/app/vulnerable_test.py"


print(
    "========== PR SEMANTIC REVIEW TEST =========="
)


# ============================================================
# 1. GET SOURCE CODE FROM GITHUB PR
# ============================================================

print(
    "\n========== FETCHING PR SOURCE CODE =========="
)

source_code = get_pull_request_file_content(
    REPOSITORY,
    PR_NUMBER,
    FILE_PATH,
)


print("\nSource code:")
print(source_code)


# ============================================================
# 2. SEND SOURCE CODE TO SEMANTIC REVIEWER
# ============================================================

print(
    "\n========== RUNNING SEMANTIC ANALYSIS =========="
)

result = review_code_semantically(
    source_code
)


# ============================================================
# 3. DISPLAY RESULT
# ============================================================

print(
    "\n========== SEMANTIC REVIEW RESULT =========="
)

print(result)