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

    If GitHub rejects REQUEST_CHANGES because the authenticated
    user is the author of the pull request, automatically
    fallback to COMMENT.
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

    try:

        review = pull_request.create_review(
            body=review_body,
            event=event,
        )

    except Exception as error:

        error_message = str(
            error
        )

        # ====================================================
        # GITHUB DOES NOT ALLOW REQUEST_CHANGES ON YOUR
        # OWN PULL REQUEST
        # ====================================================

        if (
            event == "REQUEST_CHANGES"
            and "Can not request changes on your own pull request"
            in error_message
        ):

            print(
                "\n⚠️ GitHub rejected REQUEST_CHANGES "
                "because the authenticated user is the "
                "pull request author."
            )

            print(
                "Falling back to COMMENT..."
            )

            event = "COMMENT"

            review = pull_request.create_review(
                body=review_body,
                event=event,
            )

        else:

            raise

    # ========================================================
    # SUCCESS
    # ========================================================

    print(
        "\nGitHub review successfully created."
    )

    print(
        f"Review ID: {review.id}"
    )

    print(
        f"Review state: {review.state}"
    )

    print(
        f"GitHub event posted: {event}"
    )

    return {
        "success": True,
        "review_id": review.id,
        "review_url": review.html_url,
        "event": event,
        "status": event,
    }