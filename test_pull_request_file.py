from backend.app.services.github_service import (
    get_pull_request_file_content,
)


REPOSITORY = "Phani9123/AI-Code-Review-Assistant"
PR_NUMBER = 1
FILE_PATH = "backend/app/vulnerable_test.py"


print(
    "========== PULL REQUEST FILE TEST =========="
)

content = get_pull_request_file_content(
    REPOSITORY,
    PR_NUMBER,
    FILE_PATH,
)

print("\n========== FILE CONTENT ==========")

print(content)