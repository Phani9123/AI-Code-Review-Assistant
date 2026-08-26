import os
import tempfile

from backend.app.services.github_service import (
    get_pull_request_files,
    get_pull_request_file_content,
)

from backend.app.services.bandit_service import (
    run_bandit,
)

from backend.app.services.ruff_service import (
    run_ruff,
)

from backend.app.services.semantic_review_service import (
    review_code_semantically,
)

from backend.app.services.finding_validation_service import (
    validate_and_deduplicate_findings,
)

from backend.app.services.review_report_service import (
    build_review_report,
)


# ============================================================
# SUPPORTED FILE TYPES
# ============================================================

PYTHON_EXTENSIONS = {
    ".py",
}


# ============================================================
# PRIORITY CONFIGURATION
# ============================================================

SEVERITY_PRIORITY = {
    "CRITICAL": 100,
    "HIGH": 80,
    "MEDIUM": 50,
    "LOW": 20,
}


CATEGORY_PRIORITY = {
    "security": 100,
    "bug": 90,
    "concurrency": 85,
    "database": 80,
    "resource": 75,
    "performance": 70,
    "edge_case": 65,
    "maintainability": 40,
    "testing": 30,
    "style": 10,
    "other": 0,
}


# ============================================================
# FILE TYPE CHECK
# ============================================================

def is_python_file(filename: str) -> bool:
    """
    Determine whether a changed file is a Python file.
    """

    _, extension = os.path.splitext(
        filename.lower()
    )

    return extension in PYTHON_EXTENSIONS


# ============================================================
# FINDING PRIORITY
# ============================================================

def _finding_priority(finding: dict) -> int:
    """
    Calculate a priority score for one finding.

    Security and correctness findings must outrank
    stylistic findings.

    Example:

        HIGH + security
        = 80 + 100
        = 180

        LOW + style
        = 20 + 10
        = 30
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

    severity_score = SEVERITY_PRIORITY.get(
        severity,
        0,
    )

    category_score = CATEGORY_PRIORITY.get(
        category,
        0,
    )

    return (
        severity_score
        + category_score
    )


# ============================================================
# NORMALIZE BANDIT FINDINGS
# ============================================================

def normalize_bandit_findings(
    bandit_report: dict,
) -> list:
    """
    Convert Bandit findings into the common
    finding structure.
    """

    findings = []

    for issue in bandit_report.get(
        "security_issues",
        [],
    ):

        if not isinstance(
            issue,
            dict,
        ):
            continue

        findings.append(
            {
                "source": "bandit",
                "code": issue.get(
                    "test_id"
                ),
                "category": "security",
                "severity": str(
                    issue.get(
                        "severity",
                        "LOW",
                    )
                ).upper(),
                "confidence": str(
                    issue.get(
                        "confidence",
                        "LOW",
                    )
                ).upper(),
                "line": issue.get(
                    "line"
                ),
                "end_line": issue.get(
                    "line"
                ),
                "problem": issue.get(
                    "problem",
                    "",
                ),
                "evidence": issue.get(
                    "code",
                    "",
                ),
                "why": issue.get(
                    "why",
                    "",
                ),
                "verification": "",
                "fix": issue.get(
                    "fix",
                    "",
                ),
            }
        )

    return findings


# ============================================================
# EXTRACT RUFF FIX
# ============================================================

def _extract_ruff_fix(
    fix,
) -> str:
    """
    Convert Ruff's structured fix object into
    a human-readable recommendation.
    """

    if not fix:
        return ""

    # --------------------------------------------------------
    # Ruff may return a structured dictionary.
    # --------------------------------------------------------

    if isinstance(
        fix,
        dict,
    ):

        message = fix.get(
            "message",
            "",
        )

        if message:
            return str(
                message
            ).strip()

        edits = fix.get(
            "edits",
            [],
        )

        if isinstance(
            edits,
            list,
        ):

            for edit in edits:

                if not isinstance(
                    edit,
                    dict,
                ):
                    continue

                content = edit.get(
                    "content",
                    "",
                )

                if content:
                    return (
                        "Apply this change:\n\n"
                        "```python\n"
                        f"{content}\n"
                        "```"
                    )

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    return str(
        fix
    ).strip()


# ============================================================
# NORMALIZE RUFF FINDINGS
# ============================================================

def normalize_ruff_findings(
    ruff_report: dict,
) -> list:
    """
    Convert Ruff findings into the common
    finding structure.

    Ruff's own 'error' severity does NOT automatically
    mean HIGH security severity.

    A Ruff style finding is intentionally classified
    as LOW + style.
    """

    findings = []

    for issue in ruff_report.get(
        "issues",
        [],
    ):

        if not isinstance(
            issue,
            dict,
        ):
            continue

        location = issue.get(
            "location",
            {},
        )

        if not isinstance(
            location,
            dict,
        ):
            location = {}

        end_location = issue.get(
            "end_location",
            {},
        )

        if not isinstance(
            end_location,
            dict,
        ):
            end_location = {}

        findings.append(
            {
                "source": "ruff",
                "code": issue.get(
                    "code",
                    "",
                ),
                "category": "style",
                "severity": "LOW",
                "confidence": "HIGH",
                "line": location.get(
                    "row"
                ),
                "end_line": end_location.get(
                    "row"
                ),
                "problem": issue.get(
                    "message",
                    "",
                ),
                "evidence": "",
                "why": "",
                "verification": "",
                "fix": _extract_ruff_fix(
                    issue.get(
                        "fix",
                        {},
                    )
                ),
            }
        )

    return findings


# ============================================================
# NORMALIZE SEMANTIC FINDINGS
# ============================================================

def normalize_semantic_findings(
    semantic_report: dict,
) -> list:
    """
    Convert semantic-review findings into the
    common finding structure.
    """

    findings = []

    for issue in semantic_report.get(
        "issues",
        [],
    ):

        if not isinstance(
            issue,
            dict,
        ):
            continue

        findings.append(
            {
                "source": "semantic",
                "code": None,
                "category": issue.get(
                    "category",
                    "other",
                ),
                "severity": str(
                    issue.get(
                        "severity",
                        "MEDIUM",
                    )
                ).upper(),
                "confidence": str(
                    issue.get(
                        "confidence",
                        "MEDIUM",
                    )
                ).upper(),
                "line": issue.get(
                    "line"
                ),
                "end_line": issue.get(
                    "end_line"
                ),
                "problem": issue.get(
                    "problem",
                    "",
                ),
                "evidence": issue.get(
                    "evidence",
                    "",
                ),
                "why": issue.get(
                    "why",
                    "",
                ),
                "verification": issue.get(
                    "verification",
                    "",
                ),
                "fix": issue.get(
                    "change",
                    "",
                ),
            }
        )

    return findings


# ============================================================
# AGGREGATE FINDINGS
# ============================================================

def aggregate_findings(
    bandit_report: dict,
    ruff_report: dict,
    semantic_report: dict,
) -> list:
    """
    Combine Bandit, Ruff and semantic findings
    into one list.
    """

    findings = []

    # --------------------------------------------------------
    # BANDIT
    # --------------------------------------------------------

    findings.extend(
        normalize_bandit_findings(
            bandit_report
        )
    )

    # --------------------------------------------------------
    # RUFF
    # --------------------------------------------------------

    findings.extend(
        normalize_ruff_findings(
            ruff_report
        )
    )

    # --------------------------------------------------------
    # SEMANTIC
    # --------------------------------------------------------

    findings.extend(
        normalize_semantic_findings(
            semantic_report
        )
    )

    return findings


# ============================================================
# RUN STATIC ANALYSIS
# ============================================================

def analyze_python_file(
    source_code: str,
) -> dict:
    """
    Run Bandit and Ruff against one Python source file.

    Bandit and Ruff operate on files, so the source code
    is temporarily written to disk.
    """

    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8",
    )

    file_path = temp_file.name

    try:

        temp_file.write(
            source_code
        )

        temp_file.close()

        # ====================================================
        # BANDIT
        # ====================================================

        print(
            "\n========== RUNNING BANDIT =========="
        )

        bandit_report = run_bandit(
            file_path
        )

        # ====================================================
        # RUFF
        # ====================================================

        print(
            "\n========== RUNNING RUFF =========="
        )

        ruff_report = run_ruff(
            file_path
        )

        return {
            "bandit": bandit_report,
            "ruff": ruff_report,
        }

    finally:

        if os.path.exists(
            file_path
        ):

            os.remove(
                file_path
            )

            print(
                "\nStatic analysis temporary file deleted."
            )


# ============================================================
# ANALYZE ONE PR FILE
# ============================================================

def analyze_pr_file(
    repository_name: str,
    pull_request_number: int,
    filename: str,
    patch: str = "",
) -> dict:
    """
    Analyze one changed Python file from a Pull Request.

    Pipeline:

        GitHub
          ↓
        Full source code
          ↓
        Bandit
          ↓
        Ruff
          ↓
        PR patch
          ↓
        Semantic AI
          ↓
        Aggregate
          ↓
        Validate
          ↓
        Deduplicate
          ↓
        Prioritize

    Static tools receive the complete file.

    The semantic AI reviewer receives only the GitHub
    Pull Request patch.
    """

    print(
        "\n=================================================="
    )

    print(
        f"ANALYZING FILE: {filename}"
    )

    print(
        "=================================================="
    )

    # ========================================================
    # GET SOURCE CODE
    # ========================================================

    print(
        "\n========== FETCHING SOURCE CODE =========="
    )

    source_code = get_pull_request_file_content(
        repository_name,
        pull_request_number,
        filename,
    )

    print(
        f"Source length: {len(source_code)} characters"
    )

    # ========================================================
    # STATIC ANALYSIS
    # ========================================================

    static_report = analyze_python_file(
        source_code
    )

    bandit_report = static_report[
        "bandit"
    ]

    ruff_report = static_report[
        "ruff"
    ]

    # ========================================================
    # SEMANTIC ANALYSIS
    # ========================================================

    print(
        "\n========== RUNNING SEMANTIC ANALYSIS =========="
    )

    semantic_input = patch.strip()

    if semantic_input:

        print(
            f"Semantic review input: "
            f"PR patch ({len(semantic_input)} characters)"
        )

        semantic_report = (
            review_code_semantically(
                semantic_input
            )
        )

    else:

        print(
            "\nNo GitHub patch available. "
            "Skipping semantic review."
        )

        semantic_report = {
            "issues": [],
            "error": "No PR patch available.",
        }

    # ========================================================
    # AGGREGATE FINDINGS
    # ========================================================

    print(
        "\n========== AGGREGATING FINDINGS =========="
    )

    findings = aggregate_findings(
        bandit_report,
        ruff_report,
        semantic_report,
    )

    print(
        f"Findings before validation: "
        f"{len(findings)}"
    )

    # ========================================================
    # VALIDATE + DEDUPLICATE
    # ========================================================

    print(
        "\n========== VALIDATING FINDINGS =========="
    )

    validation_result = (
        validate_and_deduplicate_findings(
            findings,
            source_code,
            filename=filename,
        )
    )

    findings = validation_result[
        "findings"
    ]

    rejected_findings = validation_result[
        "rejected"
    ]

    before_deduplication = (
        validation_result[
            "before_deduplication"
        ]
    )

    after_deduplication = (
        validation_result[
            "after_deduplication"
        ]
    )

    duplicates_removed = (
        validation_result[
            "duplicates_removed"
        ]
    )

    print(
        f"Findings after validation: "
        f"{before_deduplication}"
    )

    print(
        f"Findings after deduplication: "
        f"{after_deduplication}"
    )

    print(
        f"Rejected findings: "
        f"{len(rejected_findings)}"
    )

    print(
        f"Duplicates removed: "
        f"{duplicates_removed}"
    )

    # ========================================================
    # PRIORITIZE AFTER VALIDATION
    # ========================================================

    findings.sort(
        key=_finding_priority,
        reverse=True,
    )

    # ========================================================
    # DISPLAY PRIORITY
    # ========================================================

    print(
        "\n========== PRIORITIZED FINDINGS =========="
    )

    for index, finding in enumerate(
        findings,
        start=1,
    ):

        priority = _finding_priority(
            finding
        )

        print(
            f"\n#{index}"
        )

        print(
            f"Source: "
            f"{finding.get('source')}"
        )

        print(
            f"Category: "
            f"{finding.get('category')}"
        )

        print(
            f"Severity: "
            f"{finding.get('severity')}"
        )

        print(
            f"Confidence: "
            f"{finding.get('confidence')}"
        )

        print(
            f"Line: "
            f"{finding.get('line')}"
        )

        print(
            f"Priority score: "
            f"{priority}"
        )

        print(
            f"Problem: "
            f"{finding.get('problem')}"
        )

    # ========================================================
    # RETURN COMPLETE FILE REVIEW
    # ========================================================

    return {
        "filename": filename,
        "source_code": source_code,
        "patch": patch,

        "bandit": bandit_report,

        "ruff": ruff_report,

        "semantic": semantic_report,

        "findings": findings,

        "rejected_findings": rejected_findings,

        "duplicates_removed": duplicates_removed,

        "before_deduplication": (
            before_deduplication
        ),

        "after_deduplication": (
            after_deduplication
        ),

        "finding_count": len(
            findings
        ),
    }


# ============================================================
# REVIEW ENTIRE PULL REQUEST
# ============================================================

def review_pull_request(
    repository_name: str,
    pull_request_number: int,
) -> dict:
    """
    Analyze every supported changed file in a Pull Request.

    Current supported language:

        Python

    Unsupported files are skipped.
    """

    print(
        "\n=================================================="
    )

    print(
        "STARTING PULL REQUEST REVIEW"
    )

    print(
        "=================================================="
    )

    print(
        f"Repository: {repository_name}"
    )

    print(
        f"Pull Request: #{pull_request_number}"
    )

    # ========================================================
    # GET CHANGED FILES
    # ========================================================

    changed_files = get_pull_request_files(
        repository_name,
        pull_request_number,
    )

    print(
        f"\nChanged files: {len(changed_files)}"
    )

    results = []

    skipped_files = []

    # ========================================================
    # PROCESS EVERY FILE
    # ========================================================

    for file in changed_files:

        filename = file.get(
            "filename",
            "",
        )

        status = file.get(
            "status",
            "",
        )

        patch = file.get(
            "patch",
            "",
        ) or ""

        print(
            f"\nFile: {filename}"
        )

        print(
            f"Status: {status}"
        )

        print(
            f"Patch length: {len(patch)} characters"
        )

        # ====================================================
        # ONLY PYTHON FILES FOR NOW
        # ====================================================

        if not is_python_file(
            filename
        ):

            print(
                "Skipping unsupported file type."
            )

            skipped_files.append(
                filename
            )

            continue

        # ====================================================
        # DELETED FILES
        # ====================================================

        if status == "removed":

            print(
                "Skipping deleted file."
            )

            skipped_files.append(
                filename
            )

            continue

        # ====================================================
        # ANALYZE FILE
        # ====================================================

        result = analyze_pr_file(
            repository_name,
            pull_request_number,
            filename,
            patch,
        )

        results.append(
            result
        )

    # ========================================================
    # COMBINE ALL PR FINDINGS
    # ========================================================

    all_findings = []

    for result in results:

        filename = result.get(
            "filename"
        )

        for finding in result.get(
            "findings",
            [],
        ):

            finding_with_file = dict(
                finding
            )

            finding_with_file[
                "filename"
            ] = filename

            all_findings.append(
                finding_with_file
            )

    # ========================================================
    # SORT ENTIRE PR
    # ========================================================

    all_findings.sort(
        key=_finding_priority,
        reverse=True,
    )

    # ========================================================
    # FINAL PR RESULT
    # ========================================================

    print(
        "\n=================================================="
    )

    print(
        "PULL REQUEST REVIEW COMPLETE"
    )

    print(
        "=================================================="
    )

    print(
        f"Files analyzed: {len(results)}"
    )

    print(
        f"Files skipped: {len(skipped_files)}"
    )

    print(
        f"Total findings: {len(all_findings)}"
    )

    print(
        "\n========== FINAL PRIORITY ORDER =========="
    )

    for index, finding in enumerate(
        all_findings,
        start=1,
    ):

        print(
            f"{index}. "
            f"[{finding.get('severity')}] "
            f"{finding.get('category')} "
            f"({finding.get('source')}) "
            f"- "
            f"{finding.get('problem')}"
        )

    # ========================================================
    # GENERATE REVIEW REPORT
    # ========================================================

    print(
        "\n========== GENERATING REVIEW REPORT =========="
    )

    review_report = build_review_report(
        findings=all_findings,
        files_analyzed=len(results),
        files_skipped=len(skipped_files),
    )

    print(
        f"Review status: "
        f"{review_report['status']}"
    )

    print(
        f"Total findings: "
        f"{review_report['total_findings']}"
    )

    # ========================================================
    # FINAL PR RESULT
    # ========================================================

    return {
        "repository": repository_name,
        "pull_request": pull_request_number,

        "files_analyzed": len(
            results
        ),

        "files_skipped": len(
            skipped_files
        ),

        "skipped_files": skipped_files,

        "results": results,

        "findings": all_findings,

        "total_findings": len(
            all_findings
        ),

        # ----------------------------------------------------
        # GENERATED REVIEW REPORT
        # ----------------------------------------------------

        "review_report": review_report,

        "review_status": review_report[
            "status"
        ],

        "markdown_report": review_report[
            "markdown"
        ],
    }