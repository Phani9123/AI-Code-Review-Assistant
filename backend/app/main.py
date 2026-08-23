from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import os
import tempfile
import hmac
import hashlib

from dotenv import load_dotenv

load_dotenv()

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
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="AI Code Review Assistant",
    description=(
        "AI-powered Pull Request code review "
        "using Bandit, Ruff and Qwen."
    ),
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# GITHUB WEBHOOK SECRET
# ============================================================

GITHUB_WEBHOOK_SECRET = os.getenv(
    "GITHUB_WEBHOOK_SECRET",
    "",
)


# ============================================================
# REQUEST MODEL
# ============================================================

class CodeRequest(BaseModel):
    code: str


# ============================================================
# GITHUB WEBHOOK SIGNATURE VERIFICATION
# ============================================================

def verify_github_signature(
    payload_body: bytes,
    signature: str,
) -> bool:
    """
    Verify that the webhook request was signed
    using the configured GitHub webhook secret.
    """

    if not GITHUB_WEBHOOK_SECRET:
        print(
            "❌ GITHUB_WEBHOOK_SECRET is not configured."
        )

        return False

    if not signature:
        print(
            "❌ GitHub webhook signature is missing."
        )

        return False

    expected_signature = (
        "sha256="
        + hmac.new(
            GITHUB_WEBHOOK_SECRET.encode(
                "utf-8"
            ),
            payload_body,
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(
        expected_signature,
        signature,
    )


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():
    """
    Health check endpoint.
    """

    return {
        "message": (
            "AI Code Review Assistant API "
            "is running"
        )
    }


# ============================================================
# MANUAL CODE REVIEW ENDPOINT
# ============================================================

@app.post("/review-code")
def review_code(
    request: CodeRequest,
):
    """
    Run a semantic review against
    manually supplied source code.

    This endpoint is kept from the
    original application.
    """

    from backend.app.services.semantic_review_service import (
        review_code_semantically,
    )

    result = review_code_semantically(
        request.code
    )

    return result


# ============================================================
# GITHUB WEBHOOK
# ============================================================

@app.post("/github-webhook")
async def github_webhook(
    request: Request,
):
    """
    Receive Pull Request events from GitHub
    and automatically run the AI code review.
    """

    print(
        "\n========== GITHUB WEBHOOK RECEIVED =========="
    )

    # ========================================================
    # GET RAW REQUEST BODY
    # ========================================================

    payload_body = await request.body()

    # ========================================================
    # GET GITHUB SIGNATURE
    # ========================================================

    signature = request.headers.get(
        "X-Hub-Signature-256",
        "",
    )

    # ========================================================
    # VERIFY SIGNATURE
    # ========================================================

    if not verify_github_signature(
        payload_body,
        signature,
    ):

        print(
            "❌ Invalid GitHub webhook signature."
        )

        return {
            "success": False,
            "message": (
                "Invalid webhook signature"
            ),
        }

    print(
        "✅ GitHub webhook signature verified."
    )

    # ========================================================
    # GET GITHUB EVENT TYPE
    # ========================================================

    event = request.headers.get(
        "X-GitHub-Event",
        "",
    )

    print(
        f"GitHub event: {event}"
    )

    # ========================================================
    # ONLY HANDLE PULL REQUEST EVENTS
    # ========================================================

    if event != "pull_request":

        print(
            "Ignoring non-Pull Request event."
        )

        return {
            "success": True,
            "message": "Event ignored",
            "event": event,
        }

    # ========================================================
    # PARSE JSON PAYLOAD
    # ========================================================

    try:

        payload = await request.json()

    except Exception as error:

        print(
            f"❌ Failed to parse webhook JSON: "
            f"{error}"
        )

        return {
            "success": False,
            "message": (
                "Invalid JSON payload"
            ),
        }

    # ========================================================
    # GET PULL REQUEST ACTION
    # ========================================================

    action = payload.get(
        "action",
        "",
    )

    print(
        f"Pull Request action: {action}"
    )

    # ========================================================
    # HANDLE ONLY RELEVANT ACTIONS
    # ========================================================

    supported_actions = {
        "opened",
        "reopened",
        "synchronize",
    }

    if action not in supported_actions:

        print(
            "Pull Request action does not "
            "require an AI review."
        )

        return {
            "success": True,
            "message": "Action ignored",
            "action": action,
        }

    # ========================================================
    # GET REPOSITORY
    # ========================================================

    repository = payload.get(
        "repository",
        {},
    )

    if not isinstance(
        repository,
        dict,
    ):

        return {
            "success": False,
            "message": (
                "Repository information missing"
            ),
        }

    repository_name = repository.get(
        "full_name",
        "",
    )

    # ========================================================
    # GET PULL REQUEST
    # ========================================================

    pull_request = payload.get(
        "pull_request",
        {},
    )

    if not isinstance(
        pull_request,
        dict,
    ):

        return {
            "success": False,
            "message": (
                "Pull Request information missing"
            ),
        }

    pull_request_number = pull_request.get(
        "number",
    )

    # ========================================================
    # DISPLAY REQUEST INFORMATION
    # ========================================================

    print(
        f"Repository: {repository_name}"
    )

    print(
        f"Pull Request: #{pull_request_number}"
    )

    # ========================================================
    # VALIDATE REQUIRED INFORMATION
    # ========================================================

    if not repository_name:

        print(
            "❌ Repository name missing."
        )

        return {
            "success": False,
            "message": (
                "Repository name missing"
            ),
        }

    if not pull_request_number:

        print(
            "❌ Pull Request number missing."
        )

        return {
            "success": False,
            "message": (
                "Pull Request number missing"
            ),
        }

    # ========================================================
    # RUN EXISTING PR REVIEW PIPELINE
    # ========================================================

    print(
        "\n========== STARTING AUTOMATIC PR REVIEW =========="
    )

    try:

        review_result = review_pull_request(
            repository_name,
            pull_request_number,
        )

    except Exception as error:

        print(
            "\n❌ PR review failed:"
        )

        print(
            error
        )

        return {
            "success": False,
            "message": (
                "PR review failed"
            ),
            "error": str(error),
        }

    # ========================================================
    # GET FINDINGS
    # ========================================================

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

    # ========================================================
    # GENERATE REVIEW REPORT
    # ========================================================

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
        f"Total findings: {len(findings)}"
    )

    # ========================================================
    # DISPLAY GENERATED REPORT
    # ========================================================

    print(
        "\n========== GENERATED REPORT =========="
    )

    print(
        markdown
    )

    # ========================================================
    # POST REVIEW TO GITHUB
    # ========================================================

    print(
        "\n========== POSTING REVIEW TO GITHUB =========="
    )

    try:

        github_result = post_pull_request_review(
            repository_name,
            pull_request_number,
            markdown,
        )

    except Exception as error:

        print(
            "\n❌ Failed to post review to GitHub:"
        )

        print(
            error
        )

        return {
            "success": False,
            "message": (
                "Review generated but "
                "GitHub posting failed"
            ),
            "repository": repository_name,
            "pull_request": pull_request_number,
            "status": status,
            "findings": len(findings),
            "error": str(error),
        }

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    print(
        "\n========== AI CODE REVIEW COMPLETE =========="
    )

    print(
        f"Status: {status}"
    )

    print(
        f"GitHub result: {github_result}"
    )

    return {
        "success": True,
        "event": event,
        "action": action,
        "repository": repository_name,
        "pull_request": pull_request_number,
        "status": status,
        "findings": len(findings),
        "github_review": github_result,
    }