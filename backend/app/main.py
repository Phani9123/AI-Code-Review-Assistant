from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import os
import tempfile

from backend.app.services.bandit_service import run_bandit

from backend.app.services.ruff_service import (
    fix_ruff,
    run_ruff,
)

from backend.app.services.validation_service import (
    validate_ai_fix,
)

from backend.app.services.ai_safety_service import (
    validate_ai_output,
)

from backend.app.services.ai_service import (
    explain_bandit_report,
    explain_ruff_report,
    generate_complete_fix,
    has_ambiguous_ruff_issues,
)

from backend.app.services.semantic_review_service import (
    review_code_semantically,
)

from backend.app.services.ambiguity_service import (
    has_ambiguous_security_behavior,
)


app = FastAPI()


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODEL
# ============================================================

class CodeRequest(BaseModel):
    code: str


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "AI Code Review Assistant API is running"
    }


# ============================================================
# CODE REVIEW ENDPOINT
# ============================================================

@app.post("/review-code")
def review_code(request: CodeRequest):

    # ========================================================
    # CREATE TEMPORARY FILE FOR ORIGINAL CODE
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
        # WRITE ORIGINAL USER CODE
        # ====================================================

        temp_file.write(request.code)
        temp_file.close()

        print("\n========== TEMP FILE ==========")
        print(file_path)

        # ====================================================
        # 1. RUN BANDIT
        # ====================================================

        print(
            "\n========== RUNNING BANDIT =========="
        )

        bandit_report = run_bandit(
            file_path
        )

        print(
            "\nBandit completed successfully."
        )

        # ====================================================
        # 2. RUN RUFF
        # ====================================================

        print(
            "\n========== RUNNING RUFF =========="
        )

        ruff_report = run_ruff(
            file_path
        )

        print(
            "\nRuff completed successfully."
        )

        # ====================================================
        # 3. SEMANTIC CODE REVIEW
        # ====================================================

        print(
            "\n========== RUNNING SEMANTIC CODE REVIEW =========="
        )

        semantic_report = review_code_semantically(
            request.code
        )

        print(
            "\nSemantic review completed."
        )

        print(
            semantic_report
        )

        # ====================================================
        # 4. AI EXPLANATIONS FOR BANDIT
        # ====================================================

        print(
            "\n========== EXPLAINING BANDIT ISSUES =========="
        )

        bandit_report = explain_bandit_report(
            bandit_report,
            request.code,
        )

        # ====================================================
        # 5. AI EXPLANATIONS FOR RUFF
        # ====================================================

        print(
            "\n========== EXPLAINING RUFF ISSUES =========="
        )

        ruff_report = explain_ruff_report(
            ruff_report,
            request.code,
        )

        # ====================================================
        # 6. STORE SEMANTIC REVIEW
        # ====================================================

        ruff_report["semantic_issues"] = (
            semantic_report.get(
                "issues",
                [],
            )
        )

        # ====================================================
        # 7. CHECK RUFF AMBIGUITY
        #
        # IMPORTANT:
        #
        # Ruff ambiguity does NOT automatically stop the AI.
        #
        # Example:
        #
        #     rang(10)
        #
        # can safely become:
        #
        #     range(10)
        #
        # But:
        #
        #     print(total)
        #
        # may require manual review.
        #
        # The AI receives this context and decides.
        # ====================================================

        print(
            "\n========== CHECKING RUFF AMBIGUITY =========="
        )

        ruff_ambiguous = has_ambiguous_ruff_issues(
            ruff_report
        )

        if ruff_ambiguous:

            print(
                "\n⚠️ Potentially ambiguous Ruff issue detected."
            )

            print(
                "The AI will inspect it before generating "
                "a correction."
            )

        else:

            print(
                "\n✅ No ambiguous Ruff issue detected."
            )

        # ====================================================
        # 8. CHECK SECURITY AMBIGUITY
        # ====================================================

        print(
            "\n========== CHECKING SECURITY AMBIGUITY =========="
        )

        security_ambiguous = (
            has_ambiguous_security_behavior(
                request.code
            )
        )

        if security_ambiguous:

            print(
                "\n⚠️ Ambiguous security behavior detected."
            )

        else:

            print(
                "\n✅ No ambiguous security behavior detected."
            )

        # ====================================================
        # 9. SECURITY AMBIGUITY ONLY
        #
        # IMPORTANT:
        #
        # Do NOT block merely because Ruff is ambiguous.
        #
        # Security ambiguity is different because automatically
        # choosing between incompatible behaviors can create a
        # dangerous security regression.
        # ====================================================

        if security_ambiguous:

            print(
                "\n========== MANUAL REVIEW REQUIRED =========="
            )

            complete_fix = {
                "summary": (
                    "Manual review is required because "
                    "the source contains ambiguous security behavior."
                ),
                "fix": (
                    "The source combines potentially unsafe "
                    "evaluation or command execution and the "
                    "intended behavior cannot be determined safely."
                ),
                "corrected_code": "",
                "manual_review_required": True,
            }

            ruff_report[
                "ai_recommended_fix"
            ] = complete_fix

            validation = {
                "valid": False,
                "status": "manual_review",
                "safety_passed": False,
                "safety_issues": [],
                "bandit_issues": None,
                "ruff_issues": None,
                "bandit_report": None,
                "ruff_report": None,
                "message": (
                    "Validation was skipped because "
                    "ambiguous security behavior requires "
                    "manual review."
                ),
            }

        else:

            # =================================================
            # 10. GENERATE COMPLETE AI FIX
            # =================================================

            print(
                "\n========== GENERATING COMPLETE AI FIX =========="
            )

            complete_fix = generate_complete_fix(
                request.code,
                bandit_report,
                ruff_report,
                semantic_report,
            )

            # =================================================
            # 11. VERIFY AI RESPONSE
            # =================================================

            if not isinstance(
                complete_fix,
                dict,
            ):

                print(
                    "\n⚠️ AI returned an invalid response."
                )

                complete_fix = {
                    "summary": (
                        "The AI returned an invalid response."
                    ),
                    "fix": (
                        "The complete AI fix could not be parsed."
                    ),
                    "corrected_code": "",
                    "manual_review_required": True,
                }

            # =================================================
            # 12. GET CORRECTED CODE
            # =================================================

            corrected_code = complete_fix.get(
                "corrected_code",
                "",
            )

            if not isinstance(
                corrected_code,
                str,
            ):

                corrected_code = ""

                complete_fix[
                    "corrected_code"
                ] = ""

            # =================================================
            # 13. AI REQUESTED MANUAL REVIEW
            # =================================================

            if complete_fix.get(
                "manual_review_required",
                False,
            ):

                print(
                    "\n⚠️ AI requested manual review."
                )

                validation = {
                    "valid": False,
                    "status": "manual_review",
                    "safety_passed": False,
                    "safety_issues": [],
                    "bandit_issues": None,
                    "ruff_issues": None,
                    "bandit_report": None,
                    "ruff_report": None,
                    "message": (
                        "The AI determined that the "
                        "source behavior is ambiguous."
                    ),
                }

            # =================================================
            # 14. EMPTY AI RESPONSE
            # =================================================

            elif not corrected_code.strip():

                print(
                    "\n⚠️ AI did not return corrected code."
                )

                complete_fix[
                    "manual_review_required"
                ] = True

                validation = {
                    "valid": False,
                    "status": "manual_review",
                    "safety_passed": False,
                    "safety_issues": [],
                    "bandit_issues": None,
                    "ruff_issues": None,
                    "bandit_report": None,
                    "ruff_report": None,
                    "message": (
                        "AI did not provide corrected code."
                    ),
                }

            else:

                # =================================================
                # 15. FIRST AI SAFETY CHECK
                # =================================================

                print(
                    "\n========== CHECKING AI OUTPUT SAFETY =========="
                )

                ai_safety = validate_ai_output(
                    corrected_code
                )

                if not ai_safety.get(
                    "safe",
                    False,
                ):

                    print(
                        "\n⚠️ AI-generated code failed "
                        "additional safety checks."
                    )

                    for issue in ai_safety.get(
                        "issues",
                        [],
                    ):

                        print(
                            f"- {issue}"
                        )

                    complete_fix[
                        "summary"
                    ] = (
                        "The AI-generated correction failed "
                        "additional safety checks."
                    )

                    complete_fix[
                        "fix"
                    ] = (
                        "Manual review is required because "
                        "the AI-generated code contains a "
                        "potentially unsafe pattern."
                    )

                    complete_fix[
                        "corrected_code"
                    ] = ""

                    complete_fix[
                        "manual_review_required"
                    ] = True

                    complete_fix[
                        "safety_issues"
                    ] = ai_safety.get(
                        "issues",
                        [],
                    )

                    validation = {
                        "valid": False,
                        "status": "manual_review",
                        "safety_passed": False,
                        "safety_issues": (
                            ai_safety.get(
                                "issues",
                                [],
                            )
                        ),
                        "bandit_issues": None,
                        "ruff_issues": None,
                        "bandit_report": None,
                        "ruff_report": None,
                        "message": (
                            "AI-generated code failed "
                            "additional safety checks."
                        ),
                    }

                else:

                    print(
                        "\n✅ AI-generated code passed "
                        "safety checks."
                    )

                    # =================================================
                    # 16. CREATE TEMP FILE FOR AI CODE
                    # =================================================

                    fix_temp_file = tempfile.NamedTemporaryFile(
                        mode="w",
                        suffix=".py",
                        delete=False,
                        encoding="utf-8",
                    )

                    fix_file_path = fix_temp_file.name

                    try:

                        fix_temp_file.write(
                            corrected_code
                        )

                        fix_temp_file.close()

                        print(
                            "\n========== AI CODE BEFORE RUFF AUTO-FIX =========="
                        )

                        print(
                            corrected_code
                        )

                        # =============================================
                        # 17. APPLY RUFF AUTO-FIX
                        # =============================================

                        print(
                            "\n========== APPLYING RUFF AUTO-FIX =========="
                        )

                        fix_result = fix_ruff(
                            fix_file_path
                        )

                        print(
                            "\nRuff auto-fix completed."
                        )

                        print(
                            fix_result
                        )

                        # =============================================
                        # 18. READ FINAL CODE
                        # =============================================

                        with open(
                            fix_file_path,
                            "r",
                            encoding="utf-8",
                        ) as fixed_file:

                            corrected_code = (
                                fixed_file.read()
                            )

                        print(
                            "\n========== AI CODE AFTER RUFF AUTO-FIX =========="
                        )

                        print(
                            corrected_code
                        )

                        # =============================================
                        # 19. FINAL AI SAFETY CHECK
                        # =============================================

                        print(
                            "\n========== RECHECKING AI OUTPUT SAFETY =========="
                        )

                        final_ai_safety = (
                            validate_ai_output(
                                corrected_code
                            )
                        )

                        if not final_ai_safety.get(
                            "safe",
                            False,
                        ):

                            print(
                                "\n⚠️ Final code failed "
                                "AI safety checks."
                            )

                            complete_fix[
                                "summary"
                            ] = (
                                "The final corrected code "
                                "failed an additional safety check."
                            )

                            complete_fix[
                                "fix"
                            ] = (
                                "Manual review is required "
                                "before using the corrected code."
                            )

                            complete_fix[
                                "corrected_code"
                            ] = ""

                            complete_fix[
                                "manual_review_required"
                            ] = True

                            complete_fix[
                                "safety_issues"
                            ] = (
                                final_ai_safety.get(
                                    "issues",
                                    [],
                                )
                            )

                            validation = {
                                "valid": False,
                                "status": "manual_review",
                                "safety_passed": False,
                                "safety_issues": (
                                    final_ai_safety.get(
                                        "issues",
                                        [],
                                    )
                                ),
                                "bandit_issues": None,
                                "ruff_issues": None,
                                "bandit_report": None,
                                "ruff_report": None,
                                "message": (
                                    "The final corrected code "
                                    "failed an additional "
                                    "AI safety check."
                                ),
                            }

                        else:

                            print(
                                "\n✅ Final corrected code "
                                "passed AI safety checks."
                            )

                            # =========================================
                            # 20. UPDATE AI FIX
                            # =========================================

                            complete_fix[
                                "corrected_code"
                            ] = corrected_code

                            complete_fix[
                                "manual_review_required"
                            ] = False

                            # =========================================
                            # 21. FINAL BANDIT + RUFF VALIDATION
                            # =========================================

                            print(
                                "\n========== "
                                "VALIDATING FINAL AI FIX "
                                "=========="
                            )

                            validation = validate_ai_fix(
                                corrected_code
                            )

                            # =========================================
                            # 22. VALIDATION STATUS
                            # =========================================

                            if validation.get(
                                "valid",
                                False,
                            ):

                                validation[
                                    "status"
                                ] = "passed"

                                print(
                                    "\n✅ AI FIX PASSED VALIDATION"
                                )

                            else:

                                validation[
                                    "status"
                                ] = "failed"

                                complete_fix[
                                    "manual_review_required"
                                ] = True

                                print(
                                    "\n⚠️ AI FIX FAILED VALIDATION"
                                )

                            print(
                                "\n========== "
                                "FINAL VALIDATION COMPLETE "
                                "=========="
                            )

                    finally:

                        if os.path.exists(
                            fix_file_path
                        ):

                            os.remove(
                                fix_file_path
                            )

                            print(
                                "\nAI fix temporary file deleted."
                            )

        # ========================================================
        # 23. STORE COMPLETE FIX
        # ========================================================

        ruff_report[
            "ai_recommended_fix"
        ] = complete_fix

        # ========================================================
        # RETURN FINAL RESPONSE
        # ========================================================

        return {
            "security": bandit_report,

            "code_quality": ruff_report,

            "semantic_review": semantic_report,

            "ai_recommended_fix": (
                complete_fix
            ),

            "validation": validation,
        }

    finally:

        # ========================================================
        # DELETE ORIGINAL TEMP FILE
        # ========================================================

        if os.path.exists(
            file_path
        ):

            os.remove(
                file_path
            )

            print(
                "\nOriginal temporary file deleted."
            )