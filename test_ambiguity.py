from backend.app.services.ambiguity_service import (
    has_ambiguous_security_behavior,
)


tests = {
    "SAME INPUT TO EVAL AND SUBPROCESS": """
import subprocess

user_input = input("Enter command: ")

result = eval(user_input)

subprocess.run(
    user_input,
    shell=True,
)
""",

    "EVAL ONLY": """
user_input = input("Enter value: ")

result = eval(user_input)

print(result)
""",

    "SUBPROCESS ONLY": """
import subprocess

user_input = input("Enter command: ")

subprocess.run(
    user_input.split(),
    check=True,
)
""",

    "SEPARATE INPUTS": """
import subprocess

value = input("Enter value: ")
command = input("Enter command: ")

result = eval(value)

subprocess.run(
    command.split(),
    check=True,
)
""",

    "UNRELATED SUBPROCESS": """
import subprocess

user_input = input("Enter value: ")

result = eval(user_input)

subprocess.run(
    ["python", "script.py"],
    check=True,
)
""",
}


for name, source in tests.items():
    print()
    print("=" * 60)
    print(name)
    print("=" * 60)

    result = has_ambiguous_security_behavior(source)

    print("Ambiguous:", result)