from backend.app.services.github_service import (
    test_github_connection,
)


print(
    "========== GITHUB CONNECTION TEST =========="
)


result = test_github_connection()


print(result)