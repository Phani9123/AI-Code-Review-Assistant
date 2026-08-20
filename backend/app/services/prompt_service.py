import json


def build_bandit_prompt(
    issue,
    source_code,
):
    """
    Build the prompt used to explain a Bandit issue.

    The AI must explain the security issue without
    inventing replacement commands or functionality.
    """

    return f"""
You are a senior Python security reviewer.

Explain the reported Bandit security issue using the
ORIGINAL SOURCE CODE.

Return ONLY valid JSON.

Required JSON format:

{{
    "why": "...",
    "fix": "...",
    "secure_code": "..."
}}

Rules:

1. Explain the reported security issue accurately.

2. Do not invent functionality.

3. Do not invent commands.

4. Do not invent executables.

5. Do not replace commands with "echo".

6. Do not replace commands with "command".

7. Do not invent subprocess arguments.

8. Preserve the intended behavior whenever it is
   clearly established by the source code.

9. For hardcoded passwords, API keys, tokens,
   credentials, or secrets, recommend an environment
   variable or secure secret manager.

10. Never use a hardcoded secret fallback.

11. Never use replacement credentials such as:

    "admin123"
    "default_password"
    "your_password"
    "password"
    "secret"
    "your_secret"

12. For eval():

    Recommend ast.literal_eval() ONLY when the source
    clearly indicates that Python literals are expected.

13. Do NOT claim ast.literal_eval() can safely execute
    arbitrary Python expressions.

14. If eval() is being used for arbitrary Python
    expression execution and the intended behavior is
    unclear, do not invent a replacement.

15. For subprocess with shell=True, recommend avoiding
    shell=True only when the intended command structure
    is clearly known from the source code.

16. Do not invent a different executable merely to
    remove shell=True.

17. Do not remove subprocess execution merely to make
    Bandit pass.

18. IMPORTANT:

    If eval() and subprocess/shell execution both involve
    the SAME user-controlled input, the situation is
    ambiguous unless the intended behavior is clearly
    established by the surrounding source code.

19. In that ambiguous situation, DO NOT automatically
    choose between:

    - Python literal parsing
    - Python expression evaluation
    - shell command execution
    - subprocess argument execution

20. In that ambiguous situation, return:

{{
    "why": "The source code uses the same user-controlled input with potentially unsafe Python evaluation and command execution. The intended behavior cannot be safely determined automatically.",
    "fix": "Manual review is required. The developer must clarify whether the input is intended for Python literal parsing, Python expression evaluation, shell command execution, or subprocess argument execution.",
    "secure_code": ""
}}

21. Do not generate:

    subprocess.run(["echo", ...])

22. Do not generate:

    subprocess.run(["command", ...])

23. Do not generate a fake replacement executable.

24. Do not generate placeholder commands.

25. If a safe replacement cannot be determined,
    "secure_code" must be an empty string.

26. Do not claim that passing Bandit proves that the
    corrected program preserves behavior.

ORIGINAL SOURCE CODE:

{source_code}

BANDIT ISSUE:

{issue}
"""


def build_ruff_prompt(issue, source_code):
    return f"""
You are a senior Python software engineer performing a precise
code-quality review.

Analyze ONE Ruff issue using the ORIGINAL SOURCE CODE.

Return ONLY valid JSON.
Do not use markdown.
Do not add ```json.
Do not add any text outside the JSON.

The JSON must have exactly these fields:

{{
    "why": "...",
    "fix": "...",
    "secure_code": "..."
}}

Important:
- Explain the exact Ruff rule.
- Explain the actual problem in the provided source code.
- Give a practical fix.
- Provide corrected Python code relevant to this issue.
- Do not invent unrelated code.

For F401:
- Remove the specific unused import.
- Do not remove imports that are actually used.
- Do not add unrelated imports.

For F821:
- Explain that the referenced name is undefined.
- DO NOT invent a value for the undefined name.
- DO NOT initialize the undefined name with 0, 1, 5, 10,
  None, an empty string, or any other arbitrary value.
- For F821, distinguish between an unknown name and an obvious
  misspelling of an existing Python name.

- If an undefined name is an obvious typo of a Python built-in,
  imported name, function, variable, or identifier that is clearly
  established by the surrounding source code, correct the typo.

- A typo correction is allowed only when the intended identifier
  is unambiguous from the ORIGINAL SOURCE CODE.

- Do not treat an obvious identifier typo as an ambiguous F821.

- For example, if the source contains:
      for i in rang(10):
  and `rang` is clearly intended to be Python's built-in `range`,
  correct it to:
      for i in range(10)

- Another example:
      prit("Hello")
  should be corrected to:
      print("Hello")
  when the surrounding source clearly indicates that output is
  intended.

- Do NOT apply typo correction when multiple possible identifiers
  could reasonably match the undefined name.

- Do NOT use typo correction to invent variables, constants,
  function arguments, configuration values, or application behavior.
- DO NOT assume what the undefined variable represents.
- DO NOT create a guessed global variable.
- DO NOT create a guessed function argument value.
- If the intended value cannot be determined from the original
  source code, explicitly state that the value is unknown.
- If the undefined name is used inside a function, adding that
  name as a function parameter may be an appropriate structural
  correction.
- If you add a parameter, DO NOT invent the value passed to it.
- Do not invent or modify a function call merely to make the
  example executable.
- Do not remove the undefined variable from an expression merely
  to make Ruff pass.
- Do not silently change the program's behavior.
- If the correct value cannot be determined, the secure_code field
  may contain only the safely corrected portion, rather than a
  complete executable program.
- If insufficient information exists to safely fix the issue,
  explicitly say that manual developer input is required.

For I001:
- Correctly sort and format the imports.
- Preserve imports that are actually required.

Original Ruff Issue:
{json.dumps(issue, indent=2)}

Original Source Code:
{source_code}
"""

def build_complete_fix_prompt(
    source_code,
    bandit_report,
    ruff_report,
):
    """
    Build a compact prompt for generating one complete
    corrected Python program.

    Important:
    - Do not invent values.
    - Do not introduce unrelated functionality.
    - Preserve behavior when safely possible.
    - Manual review is required when behavior cannot
      be determined safely.
    """

    # --------------------------------------------------------
    # Keep only the useful information from Bandit
    # --------------------------------------------------------

    security_issues = []

    for issue in bandit_report.get(
        "security_issues",
        [],
    ):
        security_issues.append(
            {
                "test_id": issue.get("test_id"),
                "severity": issue.get("severity"),
                "line": issue.get("line"),
                "problem": issue.get("problem"),
            }
        )

    # --------------------------------------------------------
    # Keep only the useful information from Ruff
    # --------------------------------------------------------

    ruff_issues = []

    for issue in ruff_report.get(
        "issues",
        [],
    ):
        ruff_issues.append(
            {
                "code": issue.get("code"),
                "message": issue.get("message"),
                "line": issue.get(
                    "location",
                    {},
                ).get("row"),
                "column": issue.get(
                    "location",
                    {},
                ).get("column"),
            }
        )

    # --------------------------------------------------------
    # Complete fix prompt
    # --------------------------------------------------------

    return f"""
You are a senior Python code-review engineer.

Fix the ORIGINAL Python source code using ONLY the
reported Bandit and Ruff issues.

Return ONLY valid JSON.

Required JSON format:

{{
  "summary": "...",
  "fix": "...",
  "corrected_code": "..."
}}

============================================================
GENERAL RULES
============================================================

1. Return the COMPLETE Python program in corrected_code.

2. Fix all reported Bandit issues.

3. Fix all reported Ruff issues.

4. Preserve the original behavior whenever safely possible.

5. Do not invent functionality.

6. Remove imports reported as unused.

7. Fix import ordering when I001 is reported.

8. Do not change working code unnecessarily.

9. Do not introduce unrelated libraries or functionality.

10. Do not silently delete functionality simply to eliminate
    a security or Ruff finding.

11. corrected_code must be syntactically valid Python whenever
    a safe correction is possible.

12. corrected_code must contain the COMPLETE corrected program.

13. Do not return only changed lines.

14. Do not add placeholders such as:

    "..."
    "your_value"
    "your_password"
    "your_secret"
    "some_function()"
    "TODO"
    "implement_here"

    unless that exact placeholder already existed in the
    original source code.

============================================================
F821 RULES
============================================================

F821 means Ruff found an undefined name.

Do NOT assume that every F821 is ambiguous.

First inspect the ORIGINAL SOURCE CODE and determine whether
the undefined name is an obvious typo whose intended correction
is directly established by the surrounding code.

SAFE F821 TYPO EXAMPLE:

Original:

for i in rang(10):
    print(i)

The name "rang" is clearly an obvious typo for Python's
built-in "range" function.

Correct it to:

for i in range(10):
    print(i)

This is allowed because:

- range is a Python built-in
- the syntax is a normal for-loop
- rang is an obvious typo
- no value is invented
- no function argument is invented
- the surrounding source establishes the intended behavior

Another example:

Original:

for i in rang(2, int(num ** 0.5) + 1):
    if num % i == 0:
        ...

Correct:

for i in range(2, int(num ** 0.5) + 1):
    if num % i == 0:
        ...

============================================================
GENUINELY AMBIGUOUS F821
============================================================

If the undefined name represents a value, object, function,
configuration, dependency, or application-specific identifier
whose intended meaning cannot be established from the original
source code, DO NOT invent a correction.

Example:

def calculate():
    return total + 10

If "total" is undefined and its intended source cannot be
determined, do NOT:

- replace total with 0
- replace total with 10
- create total = 0
- create total = 10
- invent a function argument
- remove total
- replace total with None
- replace total with ""
- invent another variable

Instead return:

{{
  "summary": "Manual review is required because the intended behavior is ambiguous.",
  "fix": "The undefined name cannot be safely resolved from the available source code without inventing behavior.",
  "corrected_code": ""
}}

============================================================
F821 DECISION PROCESS
============================================================

For every F821:

1. Identify the undefined name.

2. Inspect the surrounding source code.

3. Ask whether the intended correction is directly established
   by the source.

4. If it is an obvious typo of a known Python built-in or
   clearly defined identifier, correct it.

5. If the correction would require inventing a value,
   argument, function, object, configuration, or behavior,
   do NOT correct it automatically.

6. For genuinely ambiguous F821 issues, return an empty
   corrected_code and require manual review.

Examples of safe obvious typo corrections include:

    rang -> range

when used as a normal Python range expression.

Do NOT generalize this into:

    total -> ???

because the intended meaning of total cannot be inferred
without additional information.

============================================================
HARD-CODED SECRETS
============================================================

For hardcoded passwords, API keys, tokens, credentials,
or other secrets:

Replace the hardcoded value with an environment variable
or secure secret-management mechanism.

Never use a hardcoded fallback for a secret.

Never generate:

    os.getenv("PASSWORD", "default_password")

    os.getenv("PASSWORD", "password")

    os.getenv("PASSWORD", "admin123")

    os.environ.get("PASSWORD", "default_password")

or any equivalent pattern containing a hardcoded credential
or secret fallback.

Never use these values as replacement credentials:

    "default_password"
    "your_password"
    "password"
    "secret"
    "admin123"
    "test_password"
    "default_secret"
    "your_secret"

When the intended environment-variable name is not obvious,
use:

    APP_PASSWORD

A secure replacement should follow this pattern:

    import os

    password = os.getenv("APP_PASSWORD")

    if password is None:
        raise RuntimeError(
            "APP_PASSWORD environment variable is required"
        )

Do not expose the original hardcoded secret anywhere in
corrected_code.

Do not put the original secret into:

- comments
- error messages
- variable names
- fallback values
- documentation
- strings

============================================================
EVAL RULES
============================================================

For eval():

Use ast.literal_eval() ONLY when the source code clearly
indicates that the program expects Python literals.

ast.literal_eval() must NOT be described as a safe replacement
for arbitrary Python expression execution.

Do NOT claim that ast.literal_eval() can execute arbitrary
Python expressions.

If eval() is being used for arbitrary Python expressions,
commands, or behavior that cannot be safely determined,
require manual review.

============================================================
SUBPROCESS AND SHELL RULES
============================================================

Avoid shell=True whenever possible.

If the exact command and its arguments are clearly established
by the ORIGINAL SOURCE CODE, use subprocess with an argument
list rather than shell=True.

Do NOT invent a replacement command.

Do NOT replace the command with:

    echo

Do NOT replace the command with an unrelated executable.

Do NOT remove subprocess execution merely to make Bandit pass.

Do NOT invent command arguments.

============================================================
EVAL + SUBPROCESS AMBIGUITY
============================================================

If eval() and subprocess/shell execution both involve the
same user-controlled input, treat the situation as ambiguous
unless the intended behavior is clearly established by the
surrounding source code.

Do not automatically choose between:

1. Python literal parsing
2. Python expression evaluation
3. shell command execution
4. subprocess argument execution

If the intended behavior cannot be determined, return:

{{
  "summary": "Manual review is required because the intended behavior is ambiguous.",
  "fix": "The source code combines user-controlled input with potentially unsafe evaluation or command execution. The developer must clarify the intended behavior before a safe automatic correction can be generated.",
  "corrected_code": ""
}}

Do not:

- invent a replacement command
- replace the command with "echo"
- replace the command with a different executable
- remove subprocess execution merely to make the scanner pass
- invent arguments
- invent functionality

============================================================
SECURITY-SENSITIVE RANDOMNESS
============================================================

For security-sensitive randomness, prefer the secrets module
instead of random.

Only make this change when it is required by the reported
security issue and the intended behavior is clear.

============================================================
BEHAVIOR PRESERVATION
============================================================

Do not change:

- variable names
- calculations
- function behavior
- program flow
- input/output behavior

unless the change is required to fix a reported Bandit or
Ruff issue and the intended behavior is clear.

Do not invent functionality.

Do not make the program pass Bandit or Ruff by guessing what
the developer intended.

Do not claim that passing Bandit and Ruff proves that the
corrected program preserves the original behavior.

============================================================
FINAL SAFETY CHECK
============================================================

Before returning corrected_code, verify:

- all reported Bandit issues are addressed
- all reported Ruff issues are addressed
- no hardcoded secret remains
- no hardcoded secret fallback remains
- no guessed F821 value was introduced
- no invented function argument was introduced
- no unrelated functionality was added
- no unnecessary functionality was removed
- the complete Python program is present
- the Python syntax is valid

For an obvious typo such as:

    rang(...)

changing it to:

    range(...)

is allowed when the surrounding source clearly establishes
that the Python built-in range is intended.

For a genuinely unknown identifier such as:

    total

do NOT guess.

If a safe correction cannot be made, return:

{{
  "summary": "Manual review is required.",
  "fix": "The reported issue cannot be safely resolved from the available source code without inventing behavior.",
  "corrected_code": ""
}}

============================================================
ORIGINAL SOURCE
============================================================

{source_code}

============================================================
BANDIT FINDINGS
============================================================

{json.dumps(
    security_issues,
    indent=2,
)}

============================================================
RUFF FINDINGS
============================================================

{json.dumps(
    ruff_issues,
    indent=2,
)}
"""