import json
import subprocess
import sys


def run_bandit(file_path):
    python_executable = sys.executable

    print("========== PYTHON EXECUTABLE ==========")
    print(python_executable)

    result = subprocess.run(
        [
            python_executable,
            "-m",
            "bandit",
            "-f",
            "json",
            file_path,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    print("========== BANDIT STDOUT ==========")
    print(result.stdout)

    print("========== BANDIT STDERR ==========")
    print(result.stderr)

    print("========== BANDIT RETURN CODE ==========")
    print(result.returncode)

    if not result.stdout.strip():
        raise RuntimeError(
            "Bandit did not return JSON.\n"
            f"Return code: {result.returncode}\n"
            f"Error: {result.stderr}"
        )

    try:
        raw_report = json.loads(result.stdout)

    except json.JSONDecodeError as e:
        raise RuntimeError(
            "Bandit returned invalid JSON.\n"
            f"Output: {result.stdout}\n"
            f"Error: {e}"
        )

    # --------------------------------
    # Convert Bandit results into the
    # structure used by our application
    # --------------------------------

    security_issues = []

    for issue in raw_report.get("results", []):

        security_issues.append(
            {
                "test_id": issue.get("test_id", ""),
                "test_name": issue.get("test_name", ""),
                "severity": issue.get("issue_severity", ""),
                "confidence": issue.get("issue_confidence", ""),
                "line": issue.get("line_number", 0),
                "problem": issue.get("issue_text", ""),
                "filename": issue.get("filename", ""),
                "code": issue.get("code", ""),
            }
        )

    return {
        "total_issues": len(security_issues),
        "security_issues": security_issues,
    }