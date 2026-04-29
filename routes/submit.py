from flask import Blueprint, jsonify, request, session
from extensions import get_db, groq_client
import requests
import json
import traceback
from bs4 import BeautifulSoup
from datetime import date, timedelta
import re
import time

submit_bp = Blueprint("submit", __name__)

WANDBOX_COMPILE_URL = "https://wandbox.org/api/compile.json"

COMPILER_MAP = {
    "python":     "cpython-3.12.7",
    "javascript": "nodejs-18.20.4",
    "java":       "openjdk-jdk-21+35",
    "cpp":        "gcc-13.2.0"
}

import cloudscraper
 
def fetch_problem_description(url):
    """Attempt to scrape problem description if missing."""
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Codeforces specific
            statement = soup.find('div', class_='problem-statement')
            if statement:
                # Remove unwanted sections like sample tests from the text for AI
                for div in statement.find_all('div', class_='sample-tests'):
                    div.decompose()
                return statement.get_text(separator='\n').strip()
    except:
        pass
    return None


def parse_sample_tests(samples_html):
    """Parse sample test cases from Codeforces HTML into list of (input, output) pairs."""
    if not samples_html:
        return []
    
    try:
        soup = BeautifulSoup(samples_html, 'html.parser')
        inputs = soup.find_all('div', class_='input')
        outputs = soup.find_all('div', class_='output')
        
        pairs = []
        for inp, out in zip(inputs, outputs):
            inp_pre = inp.find('pre')
            out_pre = out.find('pre')
            if inp_pre and out_pre:
                # Handle <br> tags and nested divs in Codeforces pre blocks
                # Replace <br> with newlines, then get text
                for br in inp_pre.find_all('br'):
                    br.replace_with('\n')
                for br in out_pre.find_all('br'):
                    br.replace_with('\n')
                
                # Some Codeforces problems wrap each line in a <div>
                inp_divs = inp_pre.find_all('div')
                out_divs = out_pre.find_all('div')
                
                if inp_divs:
                    input_text = '\n'.join(d.get_text().strip() for d in inp_divs)
                else:
                    input_text = inp_pre.get_text().strip()
                
                if out_divs:
                    output_text = '\n'.join(d.get_text().strip() for d in out_divs)
                else:
                    output_text = out_pre.get_text().strip()
                
                if input_text and output_text:
                    pairs.append((input_text, output_text))
        
        return pairs
    except Exception as e:
        print(f"Error parsing sample tests: {e}")
        return []


# Transient errors from Wandbox that should be retried
TRANSIENT_ERRORS = ["OCI runtime error", "Resource temporarily unavailable", "container", "crun"]

def is_transient_error(error_text):
    """Check if an error is transient (server overload) vs actual code error."""
    if not error_text:
        return False
    return any(keyword.lower() in error_text.lower() for keyword in TRANSIENT_ERRORS)


def run_with_input(code, language, stdin_text, retries=2):
    """Run code on Wandbox with specific stdin input. Retries on transient errors. Returns (output, success)."""
    payload = {
        "compiler": COMPILER_MAP[language],
        "code": code,
        "stdin": stdin_text,
        "save": False
    }
    if language == "cpp":
        payload["options"] = "warning,gnu++17"
    
    last_error = None
    for attempt in range(retries + 1):
        try:
            resp = requests.post(WANDBOX_COMPILE_URL, json=payload, timeout=30)
            if resp.status_code != 200:
                last_error = f"Server returned status {resp.status_code}"
                if attempt < retries:
                    time.sleep(2)
                    continue
                return last_error, False
            
            result = resp.json()
            exit_status = result.get("status", "0")
            success = (exit_status == "0" or exit_status == 0) and not result.get("compiler_error") and not result.get("program_error")
            output = result.get("program_output", "").strip()
            
            if not success:
                error = result.get("compiler_error") or result.get("program_error") or ""
                # Retry on transient server errors, NOT on actual code errors
                if is_transient_error(error) and attempt < retries:
                    time.sleep(2)
                    continue
                return error or output, False
            
            return output, success
        except requests.exceptions.Timeout:
            last_error = "Execution timed out"
            if attempt < retries:
                time.sleep(2)
                continue
        except Exception as e:
            last_error = str(e)
            if attempt < retries:
                time.sleep(2)
                continue
    
    return last_error, False


def normalize_output(text):
    """Normalize output for comparison: strip trailing whitespace per line, trailing newlines."""
    if not text:
        return ""
    lines = text.strip().split('\n')
    return '\n'.join(line.rstrip() for line in lines)


def mark_solved(db, cursor, user_id, problem_id):
    """Mark a problem as solved and update streak."""
    cursor.execute(
        "SELECT status FROM user_collection WHERE user_id = %s AND problem_id = %s",
        (user_id, problem_id)
    )
    if cursor.fetchone():
        cursor.execute(
            "UPDATE user_collection SET status = 'solved' WHERE user_id = %s AND problem_id = %s",
            (user_id, problem_id)
        )
        today = date.today()
        cursor.execute("SELECT last_solved_date, current_streak FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        last_date = user_data[0]
        streak = user_data[1] or 0
        if last_date != today:
            streak = streak + 1 if last_date == today - timedelta(days=1) else 1
            cursor.execute("UPDATE users SET last_solved_date = %s, current_streak = %s WHERE id = %s", (today, streak, user_id))
        db.commit()


@submit_bp.route("/api/submit", methods=["POST"])
def submit_solution():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        problem_id = data.get("problem_id")
        code = data.get("code")
        language = data.get("language", "").lower()
        user_id = session["user_id"]
        
        if not problem_id or not code or not language:
            return jsonify({"error": "Missing required fields"}), 400

        if language not in COMPILER_MAP:
            return jsonify({"error": f"Unsupported language: {language}"}), 400

        # 1. Fetch problem metadata including samples
        db, cursor = get_db()
        cursor.execute(
            "SELECT title, description, url, samples FROM global_problems WHERE id = %s",
            (problem_id,)
        )
        problem = cursor.fetchone()
        if not problem:
            cursor.close()
            return jsonify({"error": "Problem not found"}), 404
        
        problem_title, problem_desc, problem_url, samples_html = problem

        # 2. Fallback: Fetch description if missing
        if not problem_desc or len(problem_desc) < 50:
            problem_desc = fetch_problem_description(problem_url)
            if problem_desc:
                # Cache it for future use
                cursor.execute(
                    "UPDATE global_problems SET description = %s WHERE id = %s",
                    (problem_desc, problem_id)
                )
                db.commit()
            else:
                problem_desc = "Description unavailable. Please judge based on the title: " + problem_title

        # 3. Parse sample test cases
        sample_pairs = parse_sample_tests(samples_html)

        # 4. Run code against samples (in parallel) or do a basic compile check
        sample_results = []
        all_samples_passed = True
        exec_output = ""  # Store output for response

        if sample_pairs:
            # Run ALL sample tests in parallel for speed
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            futures = {}
            with ThreadPoolExecutor(max_workers=min(len(sample_pairs), 5)) as pool:
                for i, (sample_input, expected_output) in enumerate(sample_pairs):
                    future = pool.submit(run_with_input, code, language, sample_input)
                    futures[future] = (i, sample_input, expected_output)
            
            # Collect results in order
            results_by_index = {}
            for future in as_completed(futures):
                i, sample_input, expected_output = futures[future]
                actual_output, run_ok = future.result()
                
                if not run_ok:
                    results_by_index[i] = {
                        "input": sample_input,
                        "expected": expected_output,
                        "actual": actual_output or "Compilation/Runtime Error",
                        "passed": False
                    }
                else:
                    norm_expected = normalize_output(expected_output)
                    norm_actual = normalize_output(actual_output)
                    passed = (norm_expected == norm_actual)
                    results_by_index[i] = {
                        "input": sample_input,
                        "expected": expected_output,
                        "actual": actual_output,
                        "passed": passed
                    }
            
            # Sort by original order
            for i in range(len(sample_pairs)):
                sample_results.append(results_by_index[i])
            
            all_samples_passed = all(s["passed"] for s in sample_results)
            
            # Check if results indicate a server/transient error vs real code error
            first = sample_results[0]
            if not first["passed"] and first["actual"]:
                error_text = str(first["actual"])
                if is_transient_error(error_text):
                    # Server overload — not the user's fault
                    cursor.close()
                    return jsonify({
                        "status": "Server Busy",
                        "output": "",
                        "stderr": error_text,
                        "message": "Execution server is temporarily busy. Please try again in a few seconds."
                    })
                elif first["actual"] in (None, "") or "error" in error_text.lower():
                    # Actual compile/runtime error
                    cursor.close()
                    return jsonify({
                        "status": "Runtime Error",
                        "output": "",
                        "stderr": error_text,
                        "message": "Code failed to compile or execute. Fix syntax or runtime errors first."
                    })
            
            # FAST PATH: If ALL sample outputs match exactly, accept immediately
            if all_samples_passed:
                mark_solved(db, cursor, user_id, problem_id)
                cursor.close()
                return jsonify({
                    "status": "Accepted",
                    "output": sample_results[0]["actual"] if sample_results else "",
                    "message": f"All {len(sample_pairs)} sample test(s) passed! Solution accepted."
                })
        else:
            # No samples available — do a basic compile/run check
            payload = {
                "compiler": COMPILER_MAP[language],
                "code": code,
                "save": False
            }
            if language == "cpp":
                payload["options"] = "warning,gnu++17"

            exec_response = requests.post(WANDBOX_COMPILE_URL, json=payload, timeout=30)
            if exec_response.status_code != 200:
                cursor.close()
                return jsonify({"error": "Execution engine unavailable"}), 503
                
            exec_result = exec_response.json()
            exit_status = exec_result.get("status", "0")
            exec_success = (exit_status == "0" or exit_status == 0) and not exec_result.get("compiler_error") and not exec_result.get("program_error")
            
            if not exec_success:
                stderr = exec_result.get("compiler_error") or exec_result.get("program_error") or ""
                cursor.close()
                return jsonify({
                    "status": "Runtime Error",
                    "output": exec_result.get("program_output", ""),
                    "stderr": stderr,
                    "message": "Code failed to execute. Fix syntax or runtime errors first."
                })
            exec_output = exec_result.get("program_output", "")

        # 5. Stage 3: AI Logic Check (with enriched context)
        # Build sample context for the AI
        sample_context = ""
        if sample_results:
            sample_context = "\nSAMPLE TEST RESULTS:\n"
            for i, sr in enumerate(sample_results, 1):
                sample_context += f"\nTest {i}:\n"
                sample_context += f"  Input: {sr['input']}\n"
                sample_context += f"  Expected Output: {sr['expected']}\n"
                sample_context += f"  Actual Output: {sr['actual']}\n"
                sample_context += f"  Match: {'YES' if sr['passed'] else 'NO'}\n"
        elif not sample_pairs:
            sample_context = "\n(No sample test cases available for this problem)\n"

        prompt = f"""You are a competitive programming judge. Evaluate if the code correctly solves the problem.

PROBLEM: {problem_title}
STATEMENT:
{problem_desc}
{sample_context}
USER CODE ({language}):
{code}

JUDGING RULES:
- Focus ONLY on whether the code implements the correct algorithm/logic for the problem.
- Do NOT reject for coding style, variable naming, or minor formatting differences.
- If sample tests all passed, lean toward Accepted unless the logic is clearly wrong for edge cases.
- If sample tests failed, check if the logic approach is fundamentally correct but has a minor bug vs completely wrong.
- If no sample tests are available, evaluate the algorithm logic against the problem statement.

Respond ONLY with JSON: {{"decision": "Accepted" or "Rejected", "reason": "brief explanation (max 25 words)"}}"""
        
        try:
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            ai_response = json.loads(completion.choices[0].message.content)
        except Exception as ai_err:
            # If AI fails but samples all passed, accept anyway
            if sample_pairs and all_samples_passed:
                mark_solved(db, cursor, user_id, problem_id)
                cursor.close()
                return jsonify({
                    "status": "Accepted",
                    "output": exec_output,
                    "message": "Sample tests passed. AI judge unavailable but accepting based on test results."
                })
            cursor.close()
            return jsonify({"error": f"AI Judge failed: {str(ai_err)}"}), 500
            
        is_accepted = ai_response.get("decision") == "Accepted"

        if is_accepted:
            mark_solved(db, cursor, user_id, problem_id)
            cursor.close()
            
            # Build result message
            msg = f"AI Judge: {ai_response.get('reason')}"
            if sample_results:
                passed_count = sum(1 for s in sample_results if s['passed'])
                msg = f"Samples: {passed_count}/{len(sample_results)} passed. {msg}"
            
            return jsonify({
                "status": "Accepted",
                "output": exec_output,
                "message": msg
            })
        else:
            cursor.close()
            
            # Build detailed rejection message
            msg = f"Logic Mismatch: {ai_response.get('reason')}"
            if sample_results:
                failed = [s for s in sample_results if not s['passed']]
                if failed:
                    first_fail = failed[0]
                    msg += f"\n\nFailed Sample:\n  Input: {first_fail['input']}\n  Expected: {first_fail['expected']}\n  Got: {first_fail['actual']}"
            
            return jsonify({
                "status": "Rejected",
                "output": exec_output,
                "message": msg
            })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"System error: {str(e)}"}), 500
