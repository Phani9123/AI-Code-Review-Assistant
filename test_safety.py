from backend.app.services.ai_safety_service import (
    validate_ai_output,
)


# ============================================================
# SAFE CODE
# ============================================================

safe_code = """
import os

password = os.getenv("APP_PASSWORD")

if password is None:
    raise RuntimeError(
        "APP_PASSWORD environment variable is required"
    )

print(password)
"""


# ============================================================
# UNSAFE SECRET
# ============================================================

unsafe_secret = """
password = "admin123"
print(password)
"""


# ============================================================
# UNSAFE SECRET FALLBACK
# ============================================================

unsafe_fallback = """
import os

password = os.getenv(
    "APP_PASSWORD",
    "default_password"
)

print(password)
"""


# ============================================================
# UNSAFE eval
# ============================================================

unsafe_eval = """
user_input = input("Enter expression: ")

result = eval(user_input)

print(result)
"""


# ============================================================
# UNSAFE shell=True
# ============================================================

unsafe_shell = """
import subprocess

user_input = input("Enter command: ")

subprocess.run(
    user_input,
    shell=True,
)

"""


# ============================================================
# Run tests
# ============================================================

print("========== SAFE CODE ==========")
print(validate_ai_output(safe_code))

print("\n========== HARDCODED SECRET ==========")
print(validate_ai_output(unsafe_secret))

print("\n========== SECRET FALLBACK ==========")
print(validate_ai_output(unsafe_fallback))

print("\n========== UNSAFE EVAL ==========")
print(validate_ai_output(unsafe_eval))

print("\n========== SHELL TRUE ==========")
print(validate_ai_output(unsafe_shell))