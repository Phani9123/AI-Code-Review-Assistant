import { useState } from "react";
import "./App.css";

function App() {
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("python");
  const [filename, setFilename] = useState("test.py");

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ============================================================
  // REVIEW CODE
  // ============================================================

  const reviewCode = async () => {
    if (!code.trim()) {
      setError("Please enter some code.");
      return;
    }

    setLoading(true);
    setError("");
    setResults(null);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/review-code",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            language,
            filename,
            code,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          `Server Error ${response.status}`
        );
      }

      const data = await response.json();

      setResults(data);
    } catch (err) {
      console.error(err);

      setError(
        "Failed to connect to backend. Make sure FastAPI is running."
      );
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // COPY CORRECTED CODE
  // ============================================================

  const copyCorrectedCode = async () => {
    const correctedCode =
      results?.ai_recommended_fix?.corrected_code;

    if (!correctedCode) {
      return;
    }

    try {
      await navigator.clipboard.writeText(
        correctedCode
      );

      alert("Corrected code copied to clipboard!");
    } catch (err) {
      console.error(err);

      setError(
        "Failed to copy corrected code."
      );
    }
  };

  const aiRecommendedFix =
    results?.ai_recommended_fix;

  const validation =
    results?.validation;

  return (
    <div className="container">

      {/* ========================================================
          HEADER
      ======================================================== */}

      <div className="header">
        <h1>
          🤖 AI Code Review Assistant
        </h1>

        <p>
          Analyze, fix, and validate your Python code
          using Bandit, Ruff, and AI.
        </p>
      </div>


      {/* ========================================================
          INPUT
      ======================================================== */}

      <div className="input-section">

        <label>
          Language
        </label>

        <select
          value={language}
          onChange={(e) =>
            setLanguage(e.target.value)
          }
        >
          <option value="python">
            Python
          </option>
        </select>


        <label>
          Filename
        </label>

        <input
          value={filename}
          onChange={(e) =>
            setFilename(e.target.value)
          }
        />


        <label>
          Python Code
        </label>

        <textarea
          value={code}
          onChange={(e) =>
            setCode(e.target.value)
          }
          placeholder="Paste Python code here..."
          spellCheck="false"
        />


        <button
          className="review-button"
          onClick={reviewCode}
          disabled={loading}
        >
          {loading
            ? "Reviewing..."
            : "🔍 Review Code"}
        </button>

      </div>


      {/* ========================================================
          ERROR
      ======================================================== */}

      {error && (
        <div className="error">
          {error}
        </div>
      )}


      {/* ========================================================
          RESULTS
      ======================================================== */}

      {results && (
        <div className="results-container">


          {/* ====================================================
              SECURITY REPORT
          ==================================================== */}

          <div className="results">

            <h2>
              🔒 Security Report
            </h2>

            <p>
              <strong>
                Total Issues:
              </strong>{" "}
              {results.security?.total_issues ?? 0}
            </p>


            {(
              results.security?.security_issues?.length ?? 0
            ) === 0 ? (

              <div className="success-message">
                ✅ No security issues found.
              </div>

            ) : (

              results.security.security_issues.map(
                (issue, index) => (

                  <div
                    className="issue-card"
                    key={index}
                  >

                    <h3>
                      Issue #{index + 1}
                      {" — "}
                      {issue.severity}
                    </h3>

                    <p>
                      <strong>
                        Line:
                      </strong>{" "}
                      {issue.line}
                    </p>

                    <p>
                      <strong>
                        Problem:
                      </strong>{" "}
                      {issue.problem}
                    </p>

                    <p>
                      <strong>
                        Confidence:
                      </strong>{" "}
                      {issue.confidence}
                    </p>


                    <div className="ai-section">

                      <h4>
                        Why is this dangerous?
                      </h4>

                      <p>
                        {
                          issue.ai_explanation?.why ||
                          "No AI explanation available."
                        }
                      </p>

                    </div>


                    <div className="ai-section">

                      <h4>
                        How to fix it?
                      </h4>

                      <p>
                        {
                          issue.ai_explanation?.fix ||
                          "No AI fix explanation available."
                        }
                      </p>

                    </div>


                    <div className="ai-section">

                      <h4>
                        Secure Code
                      </h4>

                      <pre>
                        <code>
                          {
                            issue.ai_explanation
                              ?.secure_code ||
                            "No secure code available."
                          }
                        </code>
                      </pre>

                    </div>

                  </div>

                )
              )

            )}

          </div>


          {/* ====================================================
              RUFF REPORT
          ==================================================== */}

          <div className="results">

            <h2>
              🛠 Code Quality Report (Ruff)
            </h2>

            <p>
              <strong>
                Total Issues:
              </strong>{" "}
              {results.code_quality?.total_issues ?? 0}
            </p>


            {(
              results.code_quality?.issues?.length ?? 0
            ) === 0 ? (

              <div className="success-message">
                ✅ No code quality issues found.
              </div>

            ) : (

              results.code_quality.issues.map(
                (issue, index) => (

                  <div
                    className="issue-card"
                    key={index}
                  >

                    <h3>
                      {issue.code}
                      {" - "}
                      {issue.message}
                    </h3>

                    <p>
                      <strong>
                        File:
                      </strong>{" "}
                      {issue.filename}
                    </p>

                    <p>
                      <strong>
                        Line:
                      </strong>{" "}
                      {issue.location?.row}
                    </p>

                    <p>
                      <strong>
                        Column:
                      </strong>{" "}
                      {issue.location?.column}
                    </p>

                    <p>
                      <strong>
                        Rule:
                      </strong>{" "}
                      {issue.code}
                    </p>


                    <div className="ai-section">

                      <h4>
                        Why is this a problem?
                      </h4>

                      <p>
                        {
                          issue.ai_explanation?.why ||
                          "No AI explanation available."
                        }
                      </p>

                    </div>


                    <div className="ai-section">

                      <h4>
                        How to fix it?
                      </h4>

                      <p>
                        {
                          issue.ai_explanation?.fix ||
                          "No AI fix explanation available."
                        }
                      </p>

                    </div>


                    <div className="ai-section">

                      <h4>
                        Correct Code
                      </h4>

                      <pre>
                        <code>
                          {
                            issue.ai_explanation
                              ?.secure_code ||
                            "No corrected code available."
                          }
                        </code>
                      </pre>

                    </div>

                  </div>

                )
              )

            )}

          </div>


          {/* ====================================================
              AI RECOMMENDED FIX
          ==================================================== */}

          {aiRecommendedFix && (

            <div className="results">

              <h2>
                🤖 AI Recommended Fix
              </h2>


              <div className="ai-section">

                <h4>
                  Summary
                </h4>

                <p>
                  {
                    aiRecommendedFix.summary ||
                    "No summary available."
                  }
                </p>

              </div>


              <div className="ai-section">

                <h4>
                  How to Fix
                </h4>

                <p>
                  {
                    aiRecommendedFix.fix ||
                    "No fix available."
                  }
                </p>

              </div>


              {/* ================================================
                  MANUAL REVIEW
              ================================================= */}

              {results.ai_recommended_fix?.manual_review_required ? (
                <div className="issue-card">
                  <h2>⚠️ Manual Review Required</h2>

                  <div className="ai-section">
                    <p>
                      {results.ai_recommended_fix?.fix ||
                        "The AI cannot safely determine the intended behavior from the supplied source code."}
                    </p>
                  </div>

                  {results.ai_recommended_fix?.safety_issues?.length > 0 && (
                    <div className="ai-section">
                      <h4>Safety Issues</h4>

                      <ul>
                        {results.ai_recommended_fix.safety_issues.map(
                          (issue, index) => (
                            <li key={index}>{issue}</li>
                          )
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="ai-section">
                  <h4>Complete Corrected Code</h4>

                  <button
                    onClick={copyCorrectedCode}
                    disabled={
                      !results.ai_recommended_fix?.corrected_code
                    }
                  >
                    📋 Copy Corrected Code
                  </button>

                  <pre>
                    <code>
                      {results.ai_recommended_fix?.corrected_code ||
                        "No corrected code available."}
                    </code>
                  </pre>
                </div>
              )}

            </div>

          )}


          {/* ====================================================
              AI FIX VALIDATION
          ==================================================== */}

          {validation && (

            <div className="results">

              <h2>
                🔍 AI Fix Validation
              </h2>


              {/* ==================================================
                  PASSED
              ================================================== */}

              {validation.status === "passed" && (

                <div className="validation-card validation-passed">

                  <h3>
                    ✅ AI Fix Passed Validation
                  </h3>

                  <p>
                    The AI-generated corrected code
                    passed all validation checks.
                  </p>


                  <div className="validation-stats">

                    <div>
                      <strong>
                        Bandit Issues
                      </strong>

                      <span>
                        {validation.bandit_issues ?? 0}
                      </span>
                    </div>


                    <div>
                      <strong>
                        Ruff Issues
                      </strong>

                      <span>
                        {validation.ruff_issues ?? 0}
                      </span>
                    </div>

                  </div>


                  <p className="validation-note">
                    The corrected code passed the
                    additional AI safety check,
                    Bandit validation, and Ruff validation.
                  </p>

                </div>

              )}


              {/* ==================================================
                  FAILED
              ================================================== */}

              {validation.status === "failed" && (

                <div className="validation-card validation-failed">

                  <h3>
                    ❌ AI Fix Needs Review
                  </h3>

                  <p>
                    The AI-generated corrected code
                    still contains security or
                    code-quality issues.
                  </p>


                  <div className="validation-stats">

                    <div>
                      <strong>
                        Bandit Issues:
                      </strong>

                      <span>
                        {validation.bandit_issues ?? 0}
                      </span>
                    </div>


                    <div>
                      <strong>
                        Ruff Issues:
                      </strong>

                      <span>
                        {validation.ruff_issues ?? 0}
                      </span>
                    </div>

                  </div>


                  <p className="validation-note">
                    Review the corrected code before
                    using it.
                  </p>

                </div>

              )}


              {/* ==================================================
                  MANUAL REVIEW
              ================================================== */}

              {validation.status === "manual_review" && (

                <div className="validation-card manual-review">

                  <h3>
                    ⚠️ Manual Review Required
                  </h3>


                  {validation.safety_issues?.length > 0 ? (

                    <>
                      <p>
                        The AI-generated corrected code
                        failed additional safety checks.
                      </p>

                      <p>
                        The corrected code was blocked
                        and must be reviewed before use.
                      </p>

                      <h4>
                        Safety Issues
                      </h4>

                      <ul>

                        {validation.safety_issues.map(
                          (issue, index) => (
                            <li key={index}>
                              {issue}
                            </li>
                          )
                        )}

                      </ul>
                    </>

                  ) : (

                    <>
                      <p>
                        The AI could not safely determine
                        the intended behavior of the
                        original code.
                      </p>

                      <p>
                        Validation was skipped because
                        automatically generating a safe
                        correction could change the
                        program's intended behavior.
                      </p>
                    </>

                  )}

                </div>

              )}


              {/* ==================================================
                  UNKNOWN STATUS
              ================================================== */}

              {![
                "passed",
                "failed",
                "manual_review",
              ].includes(validation.status) && (

                <div className="validation-card manual-review">

                  <h3>
                    ⚠️ Validation Status Unknown
                  </h3>

                  <p>
                    The validation result could not
                    be determined.
                  </p>

                  <p>
                    Review the generated code manually.
                  </p>

                </div>

              )}

            </div>

          )}

        </div>
      )}

    </div>
  );
}

export default App;