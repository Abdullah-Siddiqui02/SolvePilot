from flask import Blueprint, jsonify, request
import requests

execute_bp = Blueprint("execute", __name__)

WANDBOX_COMPILE_URL = "https://wandbox.org/api/compile.json"

COMPILER_MAP = {
    "python":     "cpython-3.12.7",
    "javascript": "nodejs-18.20.4",
    "java":       "openjdk-jdk-21+35",
    "cpp":        "gcc-13.2.0"
}

@execute_bp.route("/api/execute", methods=["POST"])
def execute_code():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    language = data.get("language", "").lower()
    code = data.get("code", "")

    if language not in COMPILER_MAP:
        return jsonify({"error": f"Unsupported language: {language}"}), 400

    if not code:
        return jsonify({"error": "No code provided"}), 400

    # Prepare payload for Wandbox
    payload = {
        "compiler": COMPILER_MAP[language],
        "code": code,
        "save": False
    }

    # Add compiler options for C++
    if language == "cpp":
        payload["options"] = "warning,gnu++17"

    try:
        response = requests.post(WANDBOX_COMPILE_URL, json=payload, timeout=30)

        if response.status_code != 200:
            return jsonify({
                "error": "Execution engine error",
                "details": response.text
            }), 500

        result = response.json()

        program_output = result.get("program_output", "")
        compiler_output = result.get("compiler_output", "")
        compiler_error = result.get("compiler_error", "")
        program_error = result.get("program_error", "")
        exit_status = result.get("status", "0")

        # Determine simplified status
        if exit_status == "0" or exit_status == 0:
            status = "Success"
        elif compiler_error:
            status = "Compilation Error"
        else:
            status = "Runtime Error"

        # Combine stderr outputs
        stderr = compiler_error or program_error or ""

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
