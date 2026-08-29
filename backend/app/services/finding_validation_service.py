import re


# ============================================================
# SEVERITY PRIORITY
# ============================================================

SEVERITY_PRIORITY = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}


# ============================================================
# NORMALIZE TEXT
# ============================================================

def _normalize_text(value):
    """
    Normalize text before comparison.
    """

    if value is None:
        return ""

    text = str(value)

    text = text.replace(
        "\r\n",
        "\n",
    )

    text = text.replace(
        "\r",
        "\n",
    )

    return text.strip()


# ============================================================
# NORMALIZE CODE
# ============================================================

def _normalize_code(value):
    """
    Normalize source/evidence code for comparison.

    Removes insignificant whitespace differences
    while preserving the important tokens.
    """

    text = _normalize_text(
        value
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    text = re.sub(
        r"\s*([(),:=])\s*",
        r"\1",
        text,
    )

    return text.strip()


# ============================================================
# SOURCE LINES
# ============================================================

def _get_reported_source(
    source_code,
    line,
    end_line,
):
    """
    Extract the source lines reported by a finding.
    """

    if not isinstance(
        line,
        int,
    ):
        return ""

    if not isinstance(
        end_line,
        int,
    ):
        end_line = line

    if line < 1:
        return ""

    if end_line < line:
        return ""

    lines = source_code.splitlines()

    if line > len(lines):
        return ""

    end_line = min(
        end_line,
        len(lines),
    )

    return "\n".join(
        lines[
            line - 1:end_line
        ]
    )


# ============================================================
# EVIDENCE TOKEN EXTRACTION
# ============================================================

def _extract_meaningful_tokens(text):
    """
    Extract meaningful identifiers and keywords
    from semantic evidence.
    """

    text = _normalize_text(
        text
    )

    if not text:
        return []

    return re.findall(
        r"[A-Za-z_][A-Za-z0-9_]*",
        text,
    )


# ============================================================
# EVIDENCE MATCHING
# ============================================================

def evidence_matches_source(
    source_code,
    finding,
):
    """
    Verify that semantic evidence is supported
    by the reported source lines.

    Validation levels:

        1. Exact match
        2. Normalized match
        3. Meaningful token overlap

    Static findings may have empty evidence.
    Those findings are accepted here because
    Ruff/Bandit provide their own source information.
    """

    evidence = _normalize_text(
        finding.get(
            "evidence",
            "",
        )
    )

    # --------------------------------------------------------
    # Static findings may not contain evidence.
    # --------------------------------------------------------

    if not evidence:
        return True

    reported_source = _normalize_text(
        _get_reported_source(
            source_code,
            finding.get("line"),
            finding.get("end_line"),
        )
    )

    if not reported_source:
        return False

    # --------------------------------------------------------
    # Exact match
    # --------------------------------------------------------

    if evidence in reported_source:
        return True

    # --------------------------------------------------------
    # Normalized match
    # --------------------------------------------------------

    normalized_evidence = _normalize_code(
        evidence
    )

    normalized_source = _normalize_code(
        reported_source
    )

    if normalized_evidence in normalized_source:
        return True

    # --------------------------------------------------------
    # Token overlap
    # --------------------------------------------------------

    evidence_tokens = set(
        _extract_meaningful_tokens(
            evidence
        )
    )

    source_tokens = set(
        _extract_meaningful_tokens(
            reported_source
        )
    )

    if not evidence_tokens:
        return False

    matching_tokens = (
        evidence_tokens
        & source_tokens
    )

    overlap_ratio = (
        len(matching_tokens)
        / len(evidence_tokens)
    )

    return overlap_ratio >= 0.5


# ============================================================
# LINE RANGE VALIDATION
# ============================================================

def line_range_is_valid(
    source_code,
    finding,
):
    """
    Verify that the reported line range exists.
    """

    line = finding.get(
        "line"
    )

    end_line = finding.get(
        "end_line"
    )

    if not isinstance(
        line,
        int,
    ):
        return False

    if not isinstance(
        end_line,
        int,
    ):
        end_line = line

    if line < 1:
        return False

    if end_line < line:
        return False

    lines = source_code.splitlines()

    if line > len(lines):
        return False

    if end_line > len(lines):
        return False

    return True


# ============================================================
# FINDING VALIDATION
# ============================================================

def validate_finding(
    source_code,
    finding,
):
    """
    Validate one finding.

    Checks:

        1. Finding is a dictionary.
        2. Reported line range exists.
        3. Evidence is supported by the source.
    """

    if not isinstance(
        finding,
        dict,
    ):
        return False

    if not line_range_is_valid(
        source_code,
        finding,
    ):
        return False

    if not evidence_matches_source(
        source_code,
        finding,
    ):
        return False

    return True


# ============================================================
# DEDUPLICATION KEY
# ============================================================


def _normalize_problem_text(
    problem,
):
    """
    Normalize problem text so semantically equivalent
    static-analysis and AI findings can be compared.
    """

    text = str(
        problem or ""
    ).strip().lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


def _finding_key(
    finding,
):
    """
    Generate a file-aware deduplication key.

    The key intentionally does NOT include the complete
    problem description because different detection engines
    may describe the same underlying issue differently.

    Example:

        Bandit:
            Possible SQL injection vector through string-based
            query construction.

        Semantic:
            SQL injection vulnerability

    These should be considered the same issue when they
    point to the same file, category and line.
    """

    filename = str(
        finding.get(
            "filename",
            "",
        )
    ).strip().lower()

    category = str(
        finding.get(
            "category",
            "other",
        )
    ).strip().lower()

    line = finding.get(
        "line"
    )

    return (
        filename,
        category,
        line,
    )


# ============================================================
# DETERMINE FINDING STRENGTH
# ============================================================

def _finding_score(
    finding,
):
    """
    Calculate the strength of a finding.

    Higher score means the finding should be preferred
    when duplicate findings are detected.
    """

    severity_priority = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
    }

    confidence_priority = {
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
    }

    source_priority = {
        "semantic": 3,
        "bandit": 2,
        "ruff": 1,
    }

    severity = str(
        finding.get(
            "severity",
            "LOW",
        )
    ).upper()

    confidence = str(
        finding.get(
            "confidence",
            "LOW",
        )
    ).upper()

    source = str(
        finding.get(
            "source",
            "",
        )
    ).lower()

    return (
        severity_priority.get(
            severity,
            0,
        ),
        confidence_priority.get(
            confidence,
            0,
        ),
        source_priority.get(
            source,
            0,
        ),
    )


# ============================================================
# DEDUPLICATE FINDINGS
# ============================================================

def deduplicate_findings(
    findings,
):
    """
    Remove duplicate findings.

    Findings are considered duplicates when they point to
    the same file, category and source-code line.

    When duplicates exist, the stronger finding is kept.

    Priority:

        1. Severity
        2. Confidence
        3. Detection source

    Therefore, when Bandit and semantic analysis identify
    the same security issue:

        semantic HIGH/HIGH
                beats
        bandit MEDIUM/LOW
    """

    selected = {}

    for finding in findings:

        key = _finding_key(
            finding
        )

        existing = selected.get(
            key
        )

        if existing is None:

            selected[key] = finding

            continue

        existing_score = _finding_score(
            existing
        )

        current_score = _finding_score(
            finding
        )

        if current_score > existing_score:

            selected[key] = finding

    return list(
        selected.values()
    )

# ============================================================
# VALIDATE + DEDUPLICATE
# ============================================================

def validate_and_deduplicate_findings(
    findings,
    source_code,
    filename=None,
):
    """
    Validate findings and remove duplicates.

    IMPORTANT:
    The argument order is:

        findings,
        source_code,
        filename

    This matches the test and is easier to read.

    Returns:

        {
            "findings": [...],
            "rejected": [...],
            "before_deduplication": int,
            "after_deduplication": int,
            "duplicates_removed": int
        }
    """

    valid_findings = []

    rejected_findings = []

    # ========================================================
    # SAFETY CHECK
    # ========================================================

    if not isinstance(
        findings,
        list,
    ):

        raise TypeError(
            "findings must be a list of finding dictionaries."
        )

    if not isinstance(
        source_code,
        str,
    ):

        raise TypeError(
            "source_code must be a string."
        )

    # ========================================================
    # VALIDATION
    # ========================================================

    for finding in findings:

        # ----------------------------------------------------
        # Reject malformed findings
        # ----------------------------------------------------

        if not isinstance(
            finding,
            dict,
        ):

            rejected_findings.append(
                finding
            )

            print(
                "\nRejected malformed finding:"
            )

            print(
                finding
            )

            continue

        # ----------------------------------------------------
        # Add filename
        # ----------------------------------------------------

        if filename:

            finding = dict(
                finding
            )

            finding[
                "filename"
            ] = filename

        # ----------------------------------------------------
        # Validate
        # ----------------------------------------------------

        if validate_finding(
            source_code,
            finding,
        ):

            valid_findings.append(
                finding
            )

        else:

            rejected_findings.append(
                finding
            )

            print(
                "\nRejected finding because "
                "evidence or line range does "
                "not match the reported source."
            )

    # ========================================================
    # COUNT BEFORE DEDUPLICATION
    # ========================================================

    before_deduplication = len(
        valid_findings
    )

    # ========================================================
    # DEDUPLICATE
    # ========================================================

    deduplicated_findings = (
        deduplicate_findings(
            valid_findings
        )
    )

    # ========================================================
    # COUNT AFTER DEDUPLICATION
    # ========================================================

    after_deduplication = len(
        deduplicated_findings
    )

    duplicates_removed = (
        before_deduplication
        - after_deduplication
    )

    # ========================================================
    # RESULT
    # ========================================================

    return {
        "findings": deduplicated_findings,

        "rejected": rejected_findings,

        "before_deduplication": (
            before_deduplication
        ),

        "after_deduplication": (
            after_deduplication
        ),

        "duplicates_removed": (
            duplicates_removed
        ),
    }