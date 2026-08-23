from backend.app.services.github_service import (
    get_pull_request_info,
    get_pull_request_files,
)


REPOSITORY = "Phani9123/AI-Code-Review-Assistant"
PR_NUMBER = 1


print("========== PULL REQUEST INFO ==========")

info = get_pull_request_info(
    REPOSITORY,
    PR_NUMBER,
)

print("PR Number:", info["number"])
print("Title:", info["title"])
print("State:", info["state"])
print("Author:", info["user"])
print("Source Branch:", info["source_branch"])
print("Target Branch:", info["target_branch"])
print("Source SHA:", info["source_sha"])
print("Target SHA:", info["target_sha"])
print("URL:", info["url"])


print()
print("========== CHANGED FILES ==========")

files = get_pull_request_files(
    REPOSITORY,
    PR_NUMBER,
)

for file in files:

    print()
    print("File:", file["filename"])
    print("Status:", file["status"])
    print("Additions:", file["additions"])
    print("Deletions:", file["deletions"])
    print("Changes:", file["changes"])

    print()
    print("---------- PATCH ----------")

    print(file["patch"])