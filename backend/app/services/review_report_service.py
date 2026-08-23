from collections import Counter


# ============================================================
# SEVERITY ORDER
# ============================================================

SEVERITY_ORDER = [
    "CRITICAL",
    "HIGH",
    "MEDIUM",
    "LOW",
]


# ============================================================
# PR STATUS
# ============================================================

def determine_pr_status(findings: list) -> str:
    """
    Determine the overall Pull Request review status.

    Rules:

        CRITICAL / HIGH / MEDIUM
            -> CHANGES_REQUESTED

        Only LOW findings
            -> PASSED_WITH_WARNINGS

        No findings
            -> APPROVED
    """

    if not findings:
        return "APPROVED"

    for finding in findings:

        severity = str(
            finding.get(
                "severity",
                "LOW",
            )
        ).upper()

        if severity in {
            "CRITICAL",
            "HIGH",
            "MEDIUM",
        }:
            return "CHANGES_REQUESTED"

    return "PASSED_WITH_WARNINGS"


# ============================================================
# COUNT SEVERITIES
# ============================================================

def count_severities(findings: list) -> dict:
    """
    Count findings by severity.
    """

    counts = Counter()

    for finding in findings:

        severity = str(
            finding.get(
                "severity",
                "LOW",
            )
        ).upper()

        if severity not in SEVERITY_ORDER:
            severity = "LOW"

        counts[severity] += 1

    return {
        severity: counts.get(
            severity,
            0,
        )
        for severity in SEVERITY_ORDER
    }


# ============================================================
# COUNT CATEGORIES
# ============================================================

def count_categories(findings: list) -> dict:
    """
    Count findings by category.
    """

    counts = Counter()

    for finding in findings:

        category = str(
            finding.get(
                "category",
                "other",
            )
        ).lower()

        counts[category] += 1

    return dict(
        sorted(
            counts.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        )
    )


# ============================================================
# COUNT SOURCES
# ============================================================

def count_sources(findings: list) -> dict:
    """
    Count findings by detection source.

    Example:

        semantic
        ruff
        bandit
    """

    counts = Counter()

    for finding in findings:

        source = str(
            finding.get(
                "source",
                "unknown",
            )
        ).lower()

        counts[source] += 1

    return dict(
        sorted(
            counts.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        )
    )


# ============================================================
# FORMAT ONE FINDING
# ============================================================

def format_finding(
    finding: dict,
    index: int,
) -> str:
    """
    Convert one finding into a human-readable
    Markdown review section.
    """

    severity = str(
        finding.get(
            "severity",
            "LOW",
        )
    ).upper()

    category = str(
        finding.get(
            "category",
            "other",
        )
    ).lower()

    filename = finding.get(
        "filename",
        "Unknown file",
    )

    line = finding.get(
        "line",
        "Unknown",
    )

    end_line = finding.get(
        "end_line",
        line,
    )

    problem = finding.get(
        "problem",
        "",
    )

    evidence = finding.get(
        "evidence",
        "",
    )

    why = finding.get(
        "why",
        "",
    )

    fix = finding.get(
        "fix",
        "",
    )

    confidence = str(
        finding.get(
            "confidence",
            "MEDIUM",
        )
    ).upper()

    source = finding.get(
        "source",
        "unknown",
    )

    if end_line != line:
        line_text = (
            f"{line}-{end_line}"
        )
    else:
        line_text = str(
            line
        )

    report = []

    report.append(
        f"### Finding #{index} — "
        f"{severity} {category}"
    )

    report.append("")

    report.append(
        f"**File:** `{filename}`"
    )

    report.append(
        f"**Line:** `{line_text}`"
    )

    report.append(
        f"**Source:** `{source}`"
    )

    report.append(
        f"**Confidence:** `{confidence}`"
    )

    report.append("")

    report.append(
        f"**Problem:** {problem}"
    )

    if why:

        report.append("")

        report.append(
            f"**Why:** {why}"
        )

    if evidence:

        report.append("")

        report.append(
            "**Evidence:**"
        )

        report.append("")

        report.append(
            "```python"
        )

        report.append(
            evidence
        )

        report.append(
            "```"
        )

    if fix:

        report.append("")

        report.append(
            f"**Recommended fix:** {fix}"
        )

    return "\n".join(
        report
    )


# ============================================================
# GENERATE MARKDOWN REPORT
# ============================================================

def generate_review_report(
    findings: list,
    files_analyzed: int = 0,
    files_skipped: int = 0,
) -> str:
    """
    Generate a complete Markdown Pull Request
    review report.
    """

    if not isinstance(
        findings,
        list,
    ):
        findings = []

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    severity_counts = count_severities(
        findings
    )

    category_counts = count_categories(
        findings
    )

    source_counts = count_sources(
        findings
    )

    status = determine_pr_status(
        findings
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    report = []

    report.append(
        "# 🤖 AI Code Review"
    )

    report.append("")

    report.append(
        "Automated review generated by "
        "**AI-Code-Review-Assistant**."
    )

    report.append("")

    # --------------------------------------------------------
    # Overall status
    # --------------------------------------------------------

    report.append(
        "## Review Status"
    )

    report.append("")

    if status == "APPROVED":

        report.append(
            "### ✅ APPROVED"
        )

        report.append(
            "No meaningful issues were detected."
        )

    elif status == "PASSED_WITH_WARNINGS":

        report.append(
            "### ⚠️ PASSED WITH WARNINGS"
        )

        report.append(
            "No blocking issues were detected, "
            "but some low-severity findings remain."
        )

    else:

        report.append(
            "### ❌ CHANGES REQUESTED"
        )

        report.append(
            "The review detected issues that "
            "should be addressed before merging."
        )

    report.append("")

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    report.append(
        "## Summary"
    )

    report.append("")

    report.append(
        f"- **Files analyzed:** {files_analyzed}"
    )

    report.append(
        f"- **Files skipped:** {files_skipped}"
    )

    report.append(
        f"- **Total findings:** {len(findings)}"
    )

    report.append("")

    # --------------------------------------------------------
    # Severity summary
    # --------------------------------------------------------

    report.append(
        "## Severity Summary"
    )

    report.append("")

    report.append(
        f"- 🔴 **Critical:** "
        f"{severity_counts['CRITICAL']}"
    )

    report.append(
        f"- 🟠 **High:** "
        f"{severity_counts['HIGH']}"
    )

    report.append(
        f"- 🟡 **Medium:** "
        f"{severity_counts['MEDIUM']}"
    )

    report.append(
        f"- 🔵 **Low:** "
        f"{severity_counts['LOW']}"
    )

    report.append("")

    # --------------------------------------------------------
    # Category summary
    # --------------------------------------------------------

    report.append(
        "## Category Summary"
    )

    report.append("")

    if category_counts:

        for category, count in (
            category_counts.items()
        ):

            report.append(
                f"- **{category}:** {count}"
            )

    else:

        report.append(
            "- No findings"
        )

    report.append("")

    # --------------------------------------------------------
    # Detection source summary
    # --------------------------------------------------------

    report.append(
        "## Detection Sources"
    )

    report.append("")

    if source_counts:

        for source, count in (
            source_counts.items()
        ):

            report.append(
                f"- **{source}:** {count}"
            )

    else:

        report.append(
            "- No findings"
        )

    report.append("")

    # --------------------------------------------------------
    # Findings
    # --------------------------------------------------------

    report.append(
        "## Findings"
    )

    report.append("")

    if not findings:

        report.append(
            "🎉 No meaningful issues were detected."
        )

    else:

        for index, finding in enumerate(
            findings,
            start=1,
        ):

            report.append(
                format_finding(
                    finding,
                    index,
                )
            )

            report.append("")

            report.append(
                "---"
            )

            report.append("")

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    report.append(
        "## Review Pipeline"
    )

    report.append("")

    report.append(
        "```text"
    )

    report.append(
        "GitHub PR"
    )

    report.append(
        "    ↓"
    )

    report.append(
        "Source Code"
    )

    report.append(
        "    ↓"
    )

    report.append(
        "Bandit + Ruff"
    )

    report.append(
        "    ↓"
    )

    report.append(
        "Semantic AI Review"
    )

    report.append(
        "    ↓"
    )

    report.append(
        "Finding Validation"
    )

    report.append(
        "    ↓"
    )

    report.append(
        "Deduplication"
    )

    report.append(
        "    ↓"
    )

    report.append(
        "Priority Ordering"
    )

    report.append(
        "    ↓"
    )

    report.append(
        "Final Review"
    )

    report.append(
        "```"
    )

    return "\n".join(
        report
    )


# ============================================================
# GENERATE STRUCTURED REPORT
# ============================================================

def build_review_report(
    findings: list,
    files_analyzed: int = 0,
    files_skipped: int = 0,
) -> dict:
    """
    Return both structured statistics and the
    Markdown report.
    """

    if not isinstance(
        findings,
        list,
    ):
        findings = []

    severity_counts = count_severities(
        findings
    )

    category_counts = count_categories(
        findings
    )

    source_counts = count_sources(
        findings
    )

    status = determine_pr_status(
        findings
    )

    markdown = generate_review_report(
        findings,
        files_analyzed,
        files_skipped,
    )

    return {
        "status": status,
        "files_analyzed": files_analyzed,
        "files_skipped": files_skipped,
        "total_findings": len(findings),
        "severity_counts": severity_counts,
        "category_counts": category_counts,
        "source_counts": source_counts,
        "findings": findings,
        "markdown": markdown,
    }