import ast


def _get_user_input_variables(tree):
    """
    Find variables assigned directly from input().

    Example:
        user_input = input("Enter command: ")

    Returns:
        {"user_input"}
    """

    variables = set()

    for node in ast.walk(tree):

        if not isinstance(node, ast.Assign):
            continue

        value = node.value

        if not (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "input"
        ):
            continue

        for target in node.targets:

            if isinstance(target, ast.Name):
                variables.add(target.id)

    return variables


def _call_uses_variable(call, variable_names):
    """
    Check whether a function call directly uses one
    of the tracked user-input variables.
    """

    for argument in call.args:

        if (
            isinstance(argument, ast.Name)
            and argument.id in variable_names
        ):
            return True

    for keyword in call.keywords:

        if (
            isinstance(keyword.value, ast.Name)
            and keyword.value.id in variable_names
        ):
            return True

    return False


def _contains_subprocess_call(tree):
    """
    Check whether the source contains a subprocess call.
    """

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Attribute):
            continue

        if not isinstance(node.func.value, ast.Name):
            continue

        if node.func.value.id == "subprocess":
            return True

    return False


def _contains_shell_true(tree):
    """
    Check whether subprocess is called with shell=True.
    """

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        for keyword in node.keywords:

            if (
                keyword.arg == "shell"
                and isinstance(
                    keyword.value,
                    ast.Constant,
                )
                and keyword.value.value is True
            ):
                return True

    return False


def has_ambiguous_security_behavior(source_code: str) -> bool:
    """
    Determine whether the source combines the same
    user-controlled input with eval() and subprocess
    or shell execution.

    Returns True when automatic correction would require
    guessing the developer's intended behavior.
    """

    try:
        tree = ast.parse(source_code)

    except SyntaxError:
        return False

    user_input_variables = _get_user_input_variables(tree)

    if not user_input_variables:
        return False

    eval_uses_input = False
    subprocess_uses_input = False

    has_subprocess = _contains_subprocess_call(tree)
    has_shell_true = _contains_shell_true(tree)

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        # ====================================================
        # eval(user_input)
        # ====================================================

        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "eval"
        ):

            if _call_uses_variable(
                node,
                user_input_variables,
            ):
                eval_uses_input = True

        # ====================================================
        # subprocess.run(user_input)
        # subprocess.call(user_input)
        # etc.
        # ====================================================

        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
        ):

            if _call_uses_variable(
                node,
                user_input_variables,
            ):
                subprocess_uses_input = True

    # ========================================================
    # SAME USER INPUT -> eval()
    # AND
    # SAME USER INPUT -> subprocess
    # ========================================================

    if (
        eval_uses_input
        and subprocess_uses_input
    ):
        return True

    # ========================================================
    # USER INPUT -> eval()
    # AND subprocess uses shell=True
    #
    # The intent is ambiguous because the program combines
    # user-controlled evaluation and shell execution.
    # ========================================================

    if (
        eval_uses_input
        and has_subprocess
        and has_shell_true
    ):
        return True

    return False