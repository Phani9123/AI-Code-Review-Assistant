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
    status: str = "APPROVED",
):
    """
    Post the generated AI review to GitHub.

    Internal status:
        APPROVED
        CHANGES_REQUESTED
        COMMENT

    GitHub review events:
        APPROVE
        REQUEST_CHANGES
        COMMENT
    """

    print(
        "\n========== GITHUB REVIEW POST =========="
    )

    print(
        f"Repository: {repository_name}"
    )

    print(
        f"Pull Request: #{pull_request_number}"
    )

    print(
        f"Review status: {status}"
    )

    # ========================================================
    # MAP INTERNAL STATUS TO GITHUB EVENT
    # ========================================================

    status_to_event = {
        "APPROVED": "APPROVE",
        "CHANGES_REQUESTED": "REQUEST_CHANGES",
        "COMMENT": "COMMENT",
    }

    event = status_to_event.get(
        str(status).upper(),
        "COMMENT",
    )

    print(
        f"GitHub event: {event}"
    )

    # ========================================================
    # GET REPOSITORY
    # ========================================================

    repository = get_repository(
        repository_name
    )

    if repository is None:

        print(
            "\nCould not access GitHub repository."
        )

        return {
            "success": False,
            "message": "Could not access GitHub repository",
        }

    # ========================================================
    # GET PULL REQUEST
    # ========================================================

    pull_request = repository.get_pull(
        pull_request_number
    )

    # ========================================================
    # CREATE REVIEW
    # ========================================================

    review = pull_request.create_review(
        body=review_body,
        event=event,
    )

    print(
        "\nGitHub review successfully created."
    )

    print(
        f"Review ID: {review.id}"
    )

    print(
        f"Review state: {review.state}"
    )

    return {
        "success": True,
        "review_id": review.id,
        "review_url": review.html_url,
        "event": event,
        "status": event,
    }