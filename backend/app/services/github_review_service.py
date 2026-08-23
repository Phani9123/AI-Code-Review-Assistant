from backend.app.services.github_service import (
    get_repository,
)


# ============================================================
# POST PULL REQUEST REVIEW
# ============================================================

def post_pull_request_review(
    repository_name: str,
    pull_request_number: int,
    review_body: str,
    status: str = "COMMENT",
):
    """
    Post the generated AI code review to GitHub.

    Development behavior:

        CHANGES_REQUESTED
            -> COMMENT

        PASSED_WITH_WARNINGS
            -> COMMENT

        APPROVED
            -> COMMENT

    We currently use COMMENT because the PR author and
    GitHub token belong to the same account.

    Once a separate reviewer/bot account is used, the
    CHANGES_REQUESTED and APPROVED events can be enabled.
    """

    repository = get_repository(
        repository_name
    )

    pull_request = repository.get_pull(
        pull_request_number
    )

    # ========================================================
    # CURRENT DEVELOPMENT MODE
    # ========================================================

    event = "COMMENT"

    # ========================================================
    # SUBMIT REVIEW
    # ========================================================

    review = pull_request.create_review(
        body=review_body,
        event=event,
    )

    return {
        "success": True,
        "review_id": review.id,
        "review_url": review.html_url,
        "event": event,
        "status": status,
    }