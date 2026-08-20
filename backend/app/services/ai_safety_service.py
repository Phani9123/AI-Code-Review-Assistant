import ast
import re


# ============================================================
# Known unsafe secret values
# ============================================================

UNSAFE_SECRET_VALUES = {
    "admin123",
    "default_password",
    "your_password",
    "password",
    "secret",
    "default_secret",
    "your_secret",
    "test_password",
}


# ============================================================
# Secret detection
# ============================================================

def check_hardcoded_secrets(code: str):
    issues = []

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):

        # ----------------------------------------------------
        # Detect obvious hardcoded secret assignments
        # ----------------------------------------------------

        if isinstance(node, ast.Assign):

            for target in node.targets:

                if not isinstance(target, ast.Name):
                    continue

                variable_name = target.id.lower()

                if not any(
                    keyword in variable_name
                    for keyword in (
                        "password",
                        "passwd",
                        "secret",
                        "token",
                        "api_key",
                        "apikey",
                        "credential",
                    )
                ):
                    continue

                if isinstance(node.value, ast.Constant):
                    value = node.value.value

                    if isinstance(value, str):
                        if value.strip():
                            issues.append(
                                "AI-generated code contains a hardcoded "
                                f"secret assigned to '{target.id}'."
                            )

                        if value.lower() in UNSAFE_SECRET_VALUES:
                            issues.append(
                                "AI-generated code contains unsafe "
                                f"hardcoded secret value: '{value}'."
                            )

        # ----------------------------------------------------
        # Detect getenv/get with hardcoded fallback
        # ----------------------------------------------------

        if isinstance(node, ast.Call):

            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and node.func.attr in {
                    "getenv",
                }
            ):

                if len(node.args) >= 2:

                    fallback = node.args[1]

                    if isinstance(
                        fallback,
                        ast.Constant,
                    ) and isinstance(
                        fallback.value,
                        str,
                    ):

                        issues.append(
                            "AI-generated code uses an environment "
                            "variable with a hardcoded fallback value. "
                            "Secrets must not have hardcoded fallback "
                            "credentials."
                        )

    return issues


# ============================================================
# eval() detection
# ============================================================

def check_unsafe_eval(code: str):
    issues = []

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):

        if isinstance(node, ast.Call):

            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "eval"
            ):

                issues.append(
                    "AI-generated code uses eval(), which can execute "
                    "arbitrary Python code."
                )

    return issues


# ============================================================
# shell=True detection
# ============================================================

def check_shell_true(code: str):
    issues = []

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return issues

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        if not (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "run"
        ):
            continue

        for keyword in node.keywords:

            if keyword.arg != "shell":
                continue

            if (
                isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
            ):

                issues.append(
                    "AI-generated code uses subprocess.run() "
                    "with shell=True."
                )

    return issues


# ============================================================
# Main AI safety validator
# ============================================================

def validate_ai_output(code: str):
    """
    Independently validate AI-generated Python code.

    This validator does NOT trust the AI's explanation.
    It directly inspects the generated source code.
    """

    if not code or not code.strip():

        return {
            "safe": False,
            "issues": [
                "AI-generated code is empty."
            ],
        }

    issues = []

    # --------------------------------------------------------
    # Hardcoded secrets
    # --------------------------------------------------------

    issues.extend(
        check_hardcoded_secrets(code)
    )

    # --------------------------------------------------------
    # eval()
    # --------------------------------------------------------

    issues.extend(
        check_unsafe_eval(code)
    )

    # --------------------------------------------------------
    # shell=True
    # --------------------------------------------------------

    issues.extend(
        check_shell_true(code)
    )

    # --------------------------------------------------------
    # Remove duplicate messages
    # --------------------------------------------------------

    issues = list(
        dict.fromkeys(issues)
    )

    return {
        "safe": len(issues) == 0,
        "issues": issues,
    }