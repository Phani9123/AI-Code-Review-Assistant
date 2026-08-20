def format_bandit_report(report):

    issues = []

    for item in report["results"]:

        issue = {
            "line": item["line_number"],
            "severity": item["issue_severity"],
            "problem": item["issue_text"],
            "confidence": item["issue_confidence"]
        }

        issues.append(issue)

    return {
        "total_issues": len(issues),
        "security_issues": issues
    }