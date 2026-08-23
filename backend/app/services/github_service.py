import os

from dotenv import load_dotenv
from github import Github
from github import GithubException


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


# ============================================================
# VALIDATE TOKEN
# ============================================================

if not GITHUB_TOKEN:
    raise RuntimeError(
        "GITHUB_TOKEN is not configured. "
        "Add GITHUB_TOKEN to the .env file."
    )


# ============================================================
# CREATE GITHUB CLIENT
# ============================================================

github_client = Github(
    GITHUB_TOKEN
)


# ============================================================
# GET REPOSITORY
# ============================================================

def get_repository(repository_name: str):
    """
    Get a GitHub repository.

    Example:
        get_repository("Phani9123/Phani9123")
    """

    try:

        repository = github_client.get_repo(
            repository_name
        )

        return repository

    except GithubException as exc:

        raise RuntimeError(
            f"Could not access GitHub repository "
            f"'{repository_name}': {exc}"
        ) from exc


# ============================================================
# GET PULL REQUEST
# ============================================================

def get_pull_request(
    repository_name: str,
    pull_request_number: int,
):
    """
    Get a specific Pull Request.

    Example:
        get_pull_request(
            "Phani9123/Phani9123",
            1,
        )
    """

    repository = get_repository(
        repository_name
    )

    try:

        pull_request = repository.get_pull(
            pull_request_number
        )

        return pull_request

    except GithubException as exc:

        raise RuntimeError(
            f"Could not access Pull Request "
            f"#{pull_request_number}: {exc}"
        ) from exc


# ============================================================
# GET PULL REQUEST INFORMATION
# ============================================================

def get_pull_request_info(
    repository_name: str,
    pull_request_number: int,
):
    """
    Return basic information about a Pull Request.
    """

    pull_request = get_pull_request(
        repository_name,
        pull_request_number,
    )

    return {
        "number": pull_request.number,
        "title": pull_request.title,
        "body": pull_request.body,
        "state": pull_request.state,
        "user": pull_request.user.login,
        "source_branch": pull_request.head.ref,
        "target_branch": pull_request.base.ref,
        "source_sha": pull_request.head.sha,
        "target_sha": pull_request.base.sha,
        "url": pull_request.html_url,
    }


# ============================================================
# GET CHANGED FILES
# ============================================================

def get_pull_request_files(
    repository_name: str,
    pull_request_number: int,
):
    """
    Get files changed by the Pull Request.
    """

    pull_request = get_pull_request(
        repository_name,
        pull_request_number,
    )

    files = []

    for file in pull_request.get_files():

        files.append(
            {
                "filename": file.filename,
                "status": file.status,
                "additions": file.additions,
                "deletions": file.deletions,
                "changes": file.changes,
                "patch": file.patch,
            }
        )

    return files


# ============================================================
# GET PULL REQUEST DIFF
# ============================================================

def get_pull_request_diff(
    repository_name: str,
    pull_request_number: int,
):
    """
    Get the Pull Request diff.
    """

    pull_request = get_pull_request(
        repository_name,
        pull_request_number,
    )

    try:

        diff_response = pull_request.get_diff()

        return diff_response

    except AttributeError:

        return None

# ============================================================
# GET FILE CONTENT FROM PULL REQUEST
# ============================================================

def get_pull_request_file_content(
    repository_name: str,
    pull_request_number: int,
    file_path: str,
):
    """
    Get the actual file content from the Pull Request's
    source branch.
    """

    pull_request = get_pull_request(
        repository_name,
        pull_request_number,
    )

    repository = get_repository(
        repository_name
    )

    try:

        file_content = repository.get_contents(
            file_path,
            ref=pull_request.head.sha,
        )

        if isinstance(file_content, list):
            raise RuntimeError(
                f"'{file_path}' is a directory, not a file."
            )

        content = file_content.decoded_content.decode(
            "utf-8"
        )

        return content

    except GithubException as exc:

        raise RuntimeError(
            f"Could not retrieve file "
            f"'{file_path}' from PR "
            f"#{pull_request_number}: {exc}"
        ) from exc

# ============================================================
# TEST GITHUB CONNECTION
# ============================================================

def test_github_connection():
    """
    Verify that the GitHub token works.
    """

    try:

        user = github_client.get_user()

        return {
            "success": True,
            "username": user.login,
        }

    except GithubException as exc:

        return {
            "success": False,
            "error": str(exc),
        }
