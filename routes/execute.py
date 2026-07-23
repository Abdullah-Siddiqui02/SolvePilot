from flask import Blueprint, jsonify, request, session
import requests
import re

execute_bp = Blueprint("execute", __name__)

WANDBOX_COMPILE_URL = "https://wandbox.org/api/compile.json"

COMPILER_MAP = {
    "python":     "cpython-3.12.7",
    "javascript": "nodejs-18.20.4",
    "java":       "openjdk-jdk-21+35",
    "cpp":        "gcc-13.2.0"
}

# Transient server errors that are NOT the user's fault
TRANSIENT_KEYWORDS = ["No space left on device", "os error", "OCI runtime error",
                      "Resource temporarily unavailable", "container", "crun"]


def _is_server_error(text):
    """Check if error text indicates a server-side/transient issue."""
    if not text:
        return False
    return any(kw.lower() in text.lower() for kw in TRANSIENT_KEYWORDS)


def _format_error(error_text, language):
    """Parse error text and prepend which line(s) caused the error."""
    if not error_text:
        return error_text

    line_patterns = [
        re.compile(r'line\s+(\d+)', re.IGNORECASE),
        re.compile(r'(?:prog\.[a-z]+|Main\.java|solution\.[a-z]+):([0-9]+)'),
        re.compile(r'at\s+line\s+(\d+)', re.IGNORECASE),
    ]

    mentioned_lines = set()
    for err_line in error_text.strip().split('\n'):
        for pat in line_patterns:
            m = pat.search(err_line)
            if m:
                mentioned_lines.add(int(m.group(1)))

    result = error_text

    if mentioned_lines:
        sorted_lines = sorted(mentioned_lines)
        if len(sorted_lines) == 1:
            result = f"⚠ Error on line {sorted_lines[0]}:\n\n" + result
        else:
            line_list = ', '.join(str(l) for l in sorted_lines)
            result = f"⚠ Errors on lines {line_list}:\n\n" + result
    else:
        lower = error_text.lower()
        if 'syntaxerror' in lower or 'syntax error' in lower:
            result = "⚠ Syntax Error in your code:\n\n" + result
        elif 'nameerror' in lower:
            result = "⚠ Name Error (undefined variable/function):\n\n" + result
        elif 'typeerror' in lower:
            result = "⚠ Type Error (wrong data type):\n\n" + result
        elif 'indentationerror' in lower:
            result = "⚠ Indentation Error:\n\n" + result
        elif 'indexerror' in lower:
            result = "⚠ Index Error (out of range):\n\n" + result
        elif 'undefined reference' in lower or 'undeclared' in lower:
            result = "⚠ Compilation Error (undefined reference):\n\n" + result
        elif 'error' in lower:
            result = "⚠ Error in your code:\n\n" + result

    return result


@execute_bp.route("/api/execute", methods=["POST"])
def execute_code():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    language = data.get("language", "").lower()
    code = data.get("code", "")
    stdin = data.get("stdin", "")

    if language not in COMPILER_MAP:
        return jsonify({"error": f"Unsupported language: {language}"}), 400

    if not code:
        return jsonify({"error": "No code provided"}), 400

    # Prepare payload for Wandbox
    payload = {
        "compiler": COMPILER_MAP[language],
        "code": code,
        "stdin": stdin,
        "save": False
    }

    # Add compiler options for C++
    if language == "cpp":
        payload["options"] = "warning,gnu++17"

    try:
        response = requests.post(WANDBOX_COMPILE_URL, json=payload, timeout=30)

        if response.status_code != 200:
            # Check if it's a server-side error
            details = response.text or ""
            if _is_server_error(details):
                return jsonify({
                    "error": "Execution server is temporarily busy. Please try again in a few seconds.",
                    "details": details
                }), 503
            return jsonify({
                "error": "Execution engine error",
                "details": details
            }), 500

        result = response.json()

        program_output = result.get("program_output", "")
        compiler_output = result.get("compiler_output", "")
        compiler_error = result.get("compiler_error", "")
        program_error = result.get("program_error", "")
        exit_status = result.get("status", "0")

        # Combine stderr outputs
        stderr = compiler_error or program_error or ""

        # Check for transient server errors in stderr
        if stderr and _is_server_error(stderr):
            return jsonify({
                "error": "Execution server is temporarily busy. Please try again in a few seconds.",
                "details": stderr
            }), 503

        # Determine simplified status
        if exit_status == "0" or exit_status == 0:
            status = "Success"
        elif compiler_error:
            status = "Compilation Error"
        else:
            status = "Runtime Error"

        # Format errors with line numbers if there's an error
        if stderr and status != "Success":
            stderr = _format_error(stderr, language)

        return jsonify({
            "status": status,
            "output": program_output,
            "stderr": stderr,
            "compile_output": compiler_output
        })

    except requests.exceptions.Timeout:
        return jsonify({"error": "Execution timed out (30s limit)"}), 504
    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500
