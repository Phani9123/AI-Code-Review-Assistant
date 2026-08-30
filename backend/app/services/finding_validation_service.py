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
# ALLOWED FINDING VALUES
# ============================================================

ALLOWED_CATEGORIES = {
    "bug",
    "security",
    "performance",
    "edge_case",
    "concurrency",
    "resource",
    "database",
    "maintainability",
    "testing",
    "other",
}

ALLOWED_SEVERITIES = {
    "CRITICAL",
    "HIGH",
    "MEDIUM",
    "LOW",
}

ALLOWED_CONFIDENCES = {
    "HIGH",
    "MEDIUM",
    "LOW",
}


# ============================================================
# NORMALIZE TEXT
# ============================================================

def _normalize_text(
    value,
):
    """
    Normalize text before comparison.
    """

    if value is None:
        return ""

    text = str(
        value
    )

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

def _normalize_code(
    value,
):
    """
    Normalize source/evidence code for comparison.

    Removes insignificant whitespace differences while
    preserving important tokens.
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

def _extract_meaningful_tokens(
    text,
):
    """
    Extract identifiers and keywords from evidence.
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
# MEANINGFUL SEMANTIC EVIDENCE
# ============================================================

def _evidence_is_meaningful(
    evidence,
):
    """
    Determine whether semantic evidence contains enough
    actual code to support a finding.

    A single identifier such as:

        existing

    is not meaningful evidence.

    Examples of meaningful evidence:

        existing = selected.get(key)

        query = f"SELECT * FROM users WHERE id = '{user_id}'"
    """

    tokens = _extract_meaningful_tokens(
        evidence
    )

    if not tokens:
        return False

    trivial_tokens = {
        "if",
        "else",
        "elif",
        "for",
        "while",
        "return",
        "pass",
        "continue",
        "break",
        "true",
        "false",
        "none",
    }

    meaningful_tokens = [
        token
        for token in tokens
        if token.lower()
        not in trivial_tokens
    ]

    return len(
        meaningful_tokens
    ) >= 2


# ============================================================
# EVIDENCE MATCHING
# ============================================================

def evidence_matches_source(
    source_code,
    finding,
):
    """
    Verify that finding evidence is supported by the
    reported source lines.

    Validation levels:

        1. Exact match
        2. Normalized code match

    Token overlap is intentionally NOT accepted.

    Why?

    Evidence such as:

        existing

    can technically match the source while providing
    no useful proof that a bug exists.
    """

    evidence = _normalize_text(
        finding.get(
            "evidence",
            "",
        )
    )

    source = str(
        finding.get(
            "source",
            "",
        )
    ).lower()

    # --------------------------------------------------------
    # Static findings
    # --------------------------------------------------------

    if source in {
    "ruff",
    "bandit",
    } and not evidence:
        return True

    # --------------------------------------------------------
    # Semantic findings require evidence
    # --------------------------------------------------------

    if source == "semantic":
        if not evidence:
            return False

        if not _evidence_is_meaningful(
            evidence
        ):
            return False

    # --------------------------------------------------------
    # Generic empty evidence
    # --------------------------------------------------------

    if not evidence:
        return False

    reported_source = _normalize_text(
        _get_reported_source(
            source_code,
            finding.get(
                "line"
            ),
            finding.get(
                "end_line"
            ),
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

    # --------------------------------------------------------
    # No fuzzy token acceptance
    # --------------------------------------------------------

    return normalized_evidence in normalized_source


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
        return False

    if line < 1:
        return False

    if end_line < line:
        return False

    lines = source_code.splitlines()

    if line > len(lines):
        return False

    return not end_line > len(lines)


# ============================================================
# SEMANTIC CLAIM VALIDATION
# ============================================================

def _semantic_finding_is_valid(
    source_code,
    finding,
):
    """
    Additional conservative validation for semantic findings.

    This does not attempt to prove every possible semantic bug.

    It rejects common classes of obvious hallucinations.
    """

    problem = str(
        finding.get(
            "problem",
            "",
        )
    ).strip().lower()

    evidence = str(
        finding.get(
            "evidence",
            "",
        )
    ).strip()

    if not evidence:
        return False

    if not _evidence_is_meaningful(
        evidence
    ):
        return False

    reported_source = _get_reported_source(
        source_code,
        finding.get(
            "line"
        ),
        finding.get(
            "end_line"
        ),
    )

    if not reported_source:
        return False

    # --------------------------------------------------------
    # Undefined variable claims
    # --------------------------------------------------------

    undefined_terms = {
        "undefined",
        "not defined",
        "undefined variable",
        "nameerror",
    }

    if (
    any(
        term in problem
        for term in undefined_terms
    )
    and re.search(
        r"\b[A-Za-z_][A-Za-z0-9_]*\s*=",
        reported_source,
    )
    ):
        return False

    # --------------------------------------------------------
    # Malformed JSON / syntax claims
    # --------------------------------------------------------

    syntax_terms = {
        "malformed json",
        "invalid json",
        "syntax error",
        "invalid syntax",
        "malformed dictionary",
    }

    if any(
        term in problem
        for term in syntax_terms
    ):

        stripped = reported_source.strip()

        if (
            stripped.startswith(
                '"'
            )
            and ":"
            in stripped
        ):
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
        2. Category is allowed.
        3. Severity is allowed.
        4. Confidence is allowed.
        5. Reported line range exists.
        6. Evidence is supported by the source.
        7. Semantic findings pass additional safety checks.
    """

    if not isinstance(
        finding,
        dict,
    ):
        return False

    # ========================================================
    # NORMALIZE ENUMERATED VALUES
    # ========================================================

    category = str(
        finding.get(
            "category",
            "other",
        )
    ).lower()

    severity = str(
        finding.get(
            "severity",
            "",
        )
    ).upper()

    confidence = str(
        finding.get(
            "confidence",
            "",
        )
    ).upper()

    # ========================================================
    # VALIDATE ENUMERATED VALUES
    # ========================================================

    if category not in ALLOWED_CATEGORIES:
        return False

    if severity not in ALLOWED_SEVERITIES:
        return False

    if confidence not in ALLOWED_CONFIDENCES:
        return False

    # ========================================================
    # LINE RANGE
    # ========================================================

    if not line_range_is_valid(
        source_code,
        finding,
    ):
        return False

    # ========================================================
    # EVIDENCE
    # ========================================================

    if not evidence_matches_source(
        source_code,
        finding,
    ):
        return False

    # ========================================================
    # SOURCE
    # ========================================================

    source = str(
        finding.get(
            "source",
            "",
        )
    ).lower()

    # ========================================================
    # SEMANTIC VALIDATION
    # ========================================================

    if (
        source == "semantic"
        and not _semantic_finding_is_valid(
            source_code,
            finding,
        )
    ):
        return False


# ============================================================
# DEDUPLICATION KEY
# ============================================================

def _finding_key(
    finding,
):
    """
    Generate a file-aware deduplication key.

    The key intentionally does NOT include the complete
    problem description.

    Different engines can describe the same issue differently.

    Example:

        Bandit:
            Possible SQL injection vector through string-based
            query construction.

        Semantic:
            SQL injection vulnerability.

    These should be treated as the same issue when they refer
    to the same file/category/line.
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
# FINDING STRENGTH
# ============================================================

def _finding_score(
    finding,
):
    """
    Calculate finding strength.

    Higher score wins when duplicate findings exist.
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

    Duplicate definition:

        same filename
        +
        same category
        +
        same line

    Stronger finding wins.

    Priority:

        1. Severity
        2. Confidence
        3. Detection source
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
                "evidence, line range, "
                "enum validation, or "
                "semantic validation failed."
            )

            print(
                finding
            )

    # ========================================================
    # BEFORE DEDUPLICATION
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
    # AFTER DEDUPLICATION
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