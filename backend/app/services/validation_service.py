import os
import tempfile

from backend.app.services.ai_safety_service import (
    validate_ai_output,
)
from backend.app.services.bandit_service import run_bandit
from backend.app.services.ruff_service import run_ruff


# ============================================================
# BANDIT FINDING CLASSIFICATION
# ============================================================

# These findings indicate that the AI-generated code still
# contains a dangerous pattern that should not be accepted.
BLOCKING_BANDIT_RULES = {
    # eval()
    "B307",

    # exec()
    "B102",

    # compile()
    "B102",

    # shell=True / dangerous subprocess usage
    "B602",

    # hardcoded passwords / secrets / credentials
    "B105",
    "B106",
    "B107",

    # hardcoded cryptographic keys
    "B109",

    # weak cryptographic functions
    "B303",
    "B304",
    "B305",
    "B311",
}


# These findings can remain after a subprocess call has been
# changed to avoid shell=True.
#
# Example:
#
#     subprocess.run(args, check=True)
#
# Bandit may still report that subprocess is being used.
# That does NOT mean shell=True is still present.
#
# Because arbitrary command execution may still be intentional,
# we classify these as MANUAL REVIEW rather than pretending
# that the code is completely safe.
REVIEW_BANDIT_RULES = {
    "B404",
    "B603",
    "B606",
    "B607",
}


# ============================================================
# HELPERS
# ============================================================

def get_bandit_rule(issue):
    """
    Extract the Bandit test ID from a finding.

    Bandit reports can use different field names depending
    on how the report was processed, so check the common ones.
    """

    return str(
        issue.get("test_id")
        or issue.get("test")
        or issue.get("test_id_name")
        or ""
    ).strip().upper()


def classify_bandit_findings(bandit_report):
    """
    Classify remaining Bandit findings.

    Returns:

        {
            "blocking": [...],
            "manual_review": [...],
            "unknown": [...]
        }

    Blocking findings mean the AI-generated code still
    contains a dangerous pattern.

    Manual-review findings mean the dangerous pattern may
    have been reduced but the remaining behavior is still
    security-sensitive.

    Unknown findings are treated conservatively as blocking.
    """

    blocking = []
    manual_review = []
    unknown = []

    for issue in bandit_report.get(
        "security_issues",
        [],
    ):

        rule = get_bandit_rule(issue)

        if rule in BLOCKING_BANDIT_RULES:

            blocking.append(issue)

        elif rule in REVIEW_BANDIT_RULES:

            manual_review.append(issue)

        else:

            unknown.append(issue)

    return {
        "blocking": blocking,
        "manual_review": manual_review,
        "unknown": unknown,
    }


# ============================================================
# MAIN VALIDATION FUNCTION
# ============================================================

def validate_ai_fix(corrected_code: str):
    """
    Validate AI-generated corrected Python code.

    Validation order:

    1. AI safety validation
    2. Empty-code check
    3. Bandit security scan
    4. Ruff code-quality scan
    5. Classify remaining security findings
    6. Return PASS / MANUAL REVIEW / FAILED
    7. Temporary file cleanup

    Important:

    Passing Bandit/Ruff is not treated as proof that the
    original program's behavior has been preserved.

    The validator only determines whether the generated
    correction passed the available automated checks.
    """

    # ========================================================
    # 1. AI SAFETY VALIDATION
    # ========================================================

    safety_report = validate_ai_output(
        corrected_code
    )

    print(
        "\n========== AI SAFETY VALIDATION =========="
    )

    print(
        safety_report
    )

    # --------------------------------------------------------
    # Block unsafe AI-generated code immediately.
    # --------------------------------------------------------

    if not safety_report.get(
        "safe",
        False,
    ):

        print(
            "\n⚠️ AI-generated code failed safety validation."
        )

        return {
            "valid": False,
            "status": "failed",
            "safety_passed": False,
            "safety_issues": safety_report.get(
                "issues",
                [],
            ),
            "bandit_issues": None,
            "ruff_issues": None,
            "bandit_report": None,
            "ruff_report": None,
            "message": (
                "AI-generated code was blocked by the "
                "additional AI safety check."
            ),
        }

    print(
        "\n✅ AI safety validation passed."
    )

    # ========================================================
    # 2. CHECK EMPTY CODE
    # ========================================================

    if not corrected_code.strip():

        return {
            "valid": False,
            "status": "failed",
            "safety_passed": True,
            "safety_issues": [],
            "bandit_issues": None,
            "ruff_issues": None,
            "bandit_report": None,
            "ruff_report": None,
            "message": (
                "AI-generated corrected code is empty."
            ),
        }

    # ========================================================
    # 3. CREATE TEMPORARY FILE
    # ========================================================

    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8",
    )

    file_path = temp_file.name

    try:

        # ====================================================
        # WRITE AI-GENERATED CODE
        # ====================================================

        temp_file.write(
            corrected_code
        )

        temp_file.close()

        print(
            "\n========== VALIDATING AI FIX =========="
        )

        print(
            file_path
        )

        # ====================================================
        # 4. RUN BANDIT
        # ====================================================

        print(
            "\n========== BANDIT VALIDATION =========="
        )

        bandit_report = run_bandit(
            file_path
        )

        print(
            "\nBandit validation completed."
        )

        # ====================================================
        # 5. RUN RUFF
        # ====================================================

        print(
            "\n========== RUFF VALIDATION =========="
        )

        ruff_report = run_ruff(
            file_path
        )

        print(
            "\nRuff validation completed."
        )

        # ====================================================
        # 6. COUNT FINDINGS
        # ====================================================

        bandit_issues = len(
            bandit_report.get(
                "security_issues",
                [],
            )
        )

        ruff_issues = len(
            ruff_report.get(
                "issues",
                [],
            )
        )

        # ====================================================
        # 7. CLASSIFY BANDIT FINDINGS
        # ====================================================

        bandit_classification = (
            classify_bandit_findings(
                bandit_report
            )
        )

        blocking_bandit = (
            bandit_classification[
                "blocking"
            ]
        )

        manual_bandit = (
            bandit_classification[
                "manual_review"
            ]
        )

        unknown_bandit = (
            bandit_classification[
                "unknown"
            ]
        )

        print(
            "\n========== BANDIT CLASSIFICATION =========="
        )

        print(
            f"Total Bandit issues: {bandit_issues}"
        )

        print(
            f"Blocking issues: "
            f"{len(blocking_bandit)}"
        )

        print(
            f"Manual-review issues: "
            f"{len(manual_bandit)}"
        )

        print(
            f"Unknown issues: "
            f"{len(unknown_bandit)}"
        )

        # ====================================================
        # 8. UNKNOWN BANDIT FINDINGS
        # ====================================================

        # Unknown security rules are treated conservatively.
        #
        # We do NOT assume that an unknown Bandit finding is safe.

        if unknown_bandit:

            print(
                "\n⚠️ Unknown Bandit finding detected."
            )

            return {
                "valid": False,
                "status": "failed",
                "safety_passed": True,
                "safety_issues": [],
                "bandit_issues": bandit_issues,
                "ruff_issues": ruff_issues,
                "bandit_report": bandit_report,
                "ruff_report": ruff_report,
                "bandit_classification": (
                    bandit_classification
                ),
                "message": (
                    "The corrected code contains an "
                    "unrecognized Bandit security finding. "
                    "The correction cannot be automatically "
                    "accepted."
                ),
            }

        # ====================================================
        # 9. BLOCKING BANDIT FINDINGS
        # ====================================================

        if blocking_bandit:

            print(
                "\n❌ AI FIX FAILED BLOCKING BANDIT CHECKS."
            )

            return {
                "valid": False,
                "status": "failed",
                "safety_passed": True,
                "safety_issues": [],
                "bandit_issues": bandit_issues,
                "ruff_issues": ruff_issues,
                "bandit_report": bandit_report,
                "ruff_report": ruff_report,
                "bandit_classification": (
                    bandit_classification
                ),
                "message": (
                    "The corrected code still contains "
                    "one or more blocking security issues."
                ),
            }

        # ====================================================
        # 10. RUFF FINDINGS
        # ====================================================

        if ruff_issues > 0:

            print(
                "\n❌ AI FIX FAILED RUFF VALIDATION."
            )

            return {
                "valid": False,
                "status": "failed",
                "safety_passed": True,
                "safety_issues": [],
                "bandit_issues": bandit_issues,
                "ruff_issues": ruff_issues,
                "bandit_report": bandit_report,
                "ruff_report": ruff_report,
                "bandit_classification": (
                    bandit_classification
                ),
                "message": (
                    "The corrected code still contains "
                    "code-quality issues reported by Ruff."
                ),
            }

        # ====================================================
        # 11. MANUAL REVIEW FOR RESIDUAL SUBPROCESS FINDINGS
        # ====================================================

        if manual_bandit:

            print(
                "\n⚠️ AI FIX REQUIRES MANUAL SECURITY REVIEW."
            )

            print(
                "\nThe corrected code no longer contains "
                "a blocking Bandit pattern, but subprocess "
                "execution remains security-sensitive."
            )

            return {
                "valid": False,
                "status": "manual_review",
                "safety_passed": True,
                "safety_issues": [],
                "bandit_issues": bandit_issues,
                "ruff_issues": ruff_issues,
                "bandit_report": bandit_report,
                "ruff_report": ruff_report,
                "bandit_classification": (
                    bandit_classification
                ),
                "message": (
                    "The corrected code passed the AI safety "
                    "check and Ruff validation, but it still "
                    "contains security-sensitive subprocess "
                    "usage. Manual developer review is required."
                ),
            }

        # ====================================================
        # 12. EVERYTHING PASSED
        # ====================================================

        print(
            "\n✅ AI FIX PASSED ALL AUTOMATED VALIDATION CHECKS."
        )

        return {
            "valid": True,
            "status": "passed",
            "safety_passed": True,
            "safety_issues": [],
            "bandit_issues": bandit_issues,
            "ruff_issues": ruff_issues,
            "bandit_report": bandit_report,
            "ruff_report": ruff_report,
            "bandit_classification": (
                bandit_classification
            ),
            "message": (
                "The corrected code passed the AI safety "
                "check, Bandit validation, and Ruff validation."
            ),
        }

    finally:

        # ====================================================
        # 13. DELETE TEMPORARY FILE
        # ====================================================

        if os.path.exists(
            file_path
        ):

            os.remove(
                file_path
            )

            print(
                "\nAI validation temporary file deleted."
            )