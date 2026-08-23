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
# TEST REVIEW
# ============================================================

review_body = """
# 🤖 AI Code Review

## ❌ CHANGES REQUESTED

The automated review detected issues that should be
addressed before merging.

### 🔴 HIGH — Security

**File:** `backend/app/vulnerable_test.py`

**Line:** `2`

**Problem:** Insecure password check

**Why:**
A non-empty password is accepted without comparing it
with the stored password.

**Recommended fix:**
Compare the supplied password with the stored credential.

**Confidence:** HIGH

**Source:** Semantic AI

---

### 🔵 LOW — Style

**File:** `backend/app/vulnerable_test.py`

**Line:** `2-5`

**Problem:** Return the condition directly

**Recommended fix:**
Replace with:

`return bool(username in users and password)`

**Confidence:** HIGH

**Source:** Ruff
"""


# ============================================================
# POST REVIEW
# ============================================================

print(
    "========== POSTING GITHUB PR REVIEW =========="
)


result = post_pull_request_review(
    REPOSITORY,
    PR_NUMBER,
    review_body,
)


print(
    "\n========== RESULT =========="
)

print(
    result
)