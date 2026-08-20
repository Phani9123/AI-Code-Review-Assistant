import json
import subprocess


def run_ruff(file_path):
    """
    Run Ruff analysis on a Python file.

    Returns all Ruff issues without modifying the file.
    """

    result = subprocess.run(
        [
            "ruff",
            "check",
            "--output-format=json",
            file_path,
        ],
        capture_output=True,
        text=True,
    )

    if result.stdout.strip():
        try:
            issues = json.loads(result.stdout)
        except json.JSONDecodeError:
            issues = []
    else:
        issues = []

    return {
        "total_issues": len(issues),
        "issues": issues,
    }


def fix_ruff(file_path):
    """
    Automatically fix Ruff issues that Ruff can safely fix.

    Ruff modifies the file in place.
    """

    result = subprocess.run(
        [
            "ruff",
            "check",
            "--fix",
            file_path,
        ],
        capture_output=True,
        text=True,
    )

    return {
        "success": result.returncode in (0, 1),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }