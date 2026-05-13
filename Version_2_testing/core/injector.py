import ast
import re


def inject_docstring_into_snippet(
    *,
    code: str,
    generated_doc: str,
    language: str,
):
    """
    Inject generated documentation directly into a snippet.

    Used for inline VSCode editing.
    """

    if language == "python":
        return _inject_python_snippet(code, generated_doc)

    if language == "java":
        return _inject_java_snippet(code, generated_doc)

    if language == "javascript":
        return _inject_javascript_snippet(code, generated_doc)

    return code


def _inject_python_snippet(code: str, generated_doc: str):
    lines = code.splitlines(keepends=True)

    if not lines:
        return code

    signature_line = 0

    for idx, line in enumerate(lines):
        stripped = line.strip()

        if stripped.startswith("def ") or stripped.startswith("async def ") or stripped.startswith("class "):
            signature_line = idx
            break

    indent_match = re.match(r"^(\s*)", lines[signature_line])
    base_indent = indent_match.group(1)
    body_indent = base_indent + "    "

    doc_lines = generated_doc.strip().split("\n")

    formatted = []
    formatted.append(body_indent + '"""' + doc_lines[0] + "\n")

    for line in doc_lines[1:]:
        formatted.append(body_indent + line + "\n")

    formatted.append(body_indent + '"""\n')

    insert_idx = signature_line + 1

    # Replace existing docstring if present
    try:
        parsed = ast.parse(code)

        first_node = parsed.body[0]

        if (
            first_node.body
            and isinstance(first_node.body[0], ast.Expr)
            and isinstance(first_node.body[0].value, ast.Constant)
            and isinstance(first_node.body[0].value.value, str)
        ):
            existing_doc = first_node.body[0]

            start = existing_doc.lineno - 1
            end = existing_doc.end_lineno

            lines[start:end] = formatted

            return "".join(lines)

    except Exception:
        pass

    lines[insert_idx:insert_idx] = formatted

    return "".join(lines)



def _inject_java_snippet(code: str, generated_doc: str):
    lines = code.splitlines(keepends=True)

    if not lines:
        return code

    indent_match = re.match(r"^(\s*)", lines[0])
    indent = indent_match.group(1)

    doc_lines = generated_doc.strip().split("\n")

    formatted = [indent + "/**\n"]

    for line in doc_lines:
        formatted.append(indent + " * " + line + "\n")

    formatted.append(indent + " */\n")

    return "".join(formatted) + code



def _inject_javascript_snippet(code: str, generated_doc: str):
    lines = code.splitlines(keepends=True)

    if not lines:
        return code

    indent_match = re.match(r"^(\s*)", lines[0])
    indent = indent_match.group(1)

    doc_lines = generated_doc.strip().split("\n")

    formatted = [indent + "/**\n"]

    for line in doc_lines:
        formatted.append(indent + " * " + line + "\n")

    formatted.append(indent + " */\n")

    return "".join(formatted) + code