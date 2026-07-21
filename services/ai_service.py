import os
import json
import re
import hashlib
import logging
from time import perf_counter
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from services.prompt_builder import PromptBuilder


logger = logging.getLogger(__name__)


# Gracefully import database and AI clients from extensions
try:
    from extensions import groq_client
except ImportError:
    groq_client = None


# ──────────────────────────────────────────────────────────────
# Helper Functions and Constants (Migrated from routes/ai.py)
# ──────────────────────────────────────────────────────────────

def _classify_status(execution_status: str, compiler_output: str, action_type: str) -> str:
    """Map raw execution/submission status to a canonical mentor category.

    Returns one of:
        'compilation_error', 'runtime_error', 'wrong_answer',
        'time_limit_exceeded', 'memory_limit_exceeded', 'accepted'
    """
    s = (execution_status or "").lower().strip()

    if s in ("compilation error", "compilation_error", "compile error", "compile_error"):
        return "compilation_error"
    if s in ("runtime error", "runtime_error"):
        return "runtime_error"
    if s in ("rejected", "wrong answer", "wrong_answer"):
        return "wrong_answer"
    if "time" in s and ("limit" in s or "exceeded" in s):
        return "time_limit_exceeded"
    if "memory" in s and ("limit" in s or "exceeded" in s):
        return "memory_limit_exceeded"
    if s in ("accepted", "success"):
        return "accepted"

    # Fallback heuristic: check stderr content
    stderr = (compiler_output or "").lower()
    if "error" in stderr and ("compile" in stderr or "syntax" in stderr):
        return "compilation_error"
    if "error" in stderr:
        return "runtime_error"

    return "accepted"


# Removed hardcoded optimized code snippets


MENTOR_RESPONSES = {
    "compilation_error": {
        "error_type": "Compilation Error",
        "explanation": (
            "Your code failed to compile. This usually means there is a syntax "
            "mistake — a missing semicolon, unmatched bracket, undeclared variable, "
            "or incorrect type usage. Read the compiler error message carefully; "
            "it tells you exactly which line and character caused the problem."
        ),
        "hint": (
            "Look at the line number reported in the error. Check for missing "
            "semicolons, mismatched parentheses/braces, or misspelled keywords. "
            "If you recently changed something, undo that change and re-compile."
        ),
        "review": (
            "The code cannot be reviewed for logic because it does not compile. "
            "Fix all syntax errors first, then re-run to get a logic review."
        ),
        "complexity": {"time": "—", "space": "—"},
        "edge_cases": [
            "Ensure all variables are declared before use.",
            "Check for missing imports or include statements.",
            "Verify bracket and parenthesis matching.",
            "Confirm correct function signatures and return types."
        ],
    },

    "runtime_error": {
        "error_type": "Runtime Error",
        "explanation": (
            "Your code compiled successfully but crashed during execution. "
            "Common causes include division by zero, array index out of bounds, "
            "null pointer dereference, stack overflow from infinite recursion, "
            "or reading past the end of input."
        ),
        "hint": (
            "Check your loop boundaries and array indices. Make sure you handle "
            "edge cases like empty input or single-element arrays. Add bounds "
            "checks before accessing array elements."
        ),
        "review": (
            "The algorithm approach may be correct, but the implementation has "
            "a bug that causes a crash. Focus on defensive programming — validate "
            "inputs and indices before using them."
        ),
        "complexity": {"time": "—", "space": "—"},
        "edge_cases": [
            "Empty input or zero-length arrays.",
            "Single element input.",
            "Very large values that may cause overflow.",
            "Null or undefined values in the data.",
            "Recursive calls without a proper base case."
        ],
    },

    "wrong_answer": {
        "error_type": "Wrong Answer",
        "explanation": (
            "Your code compiled and ran without crashing, but produced incorrect "
            "output. This means the algorithm logic has a flaw — either the "
            "approach is wrong, or there is a subtle bug in how you handle "
            "certain inputs."
        ),
        "hint": (
            "Compare your output with the expected output carefully. Trace "
            "through your algorithm with the failing test case by hand. Look "
            "for off-by-one errors, incorrect comparisons, or missed edge cases."
        ),
        "review": (
            "The code structure looks reasonable, but the logic does not produce "
            "correct results for all test cases. Re-examine your core algorithm "
            "and verify it handles the problem constraints correctly."
        ),
        "complexity": {"time": "O(N)", "space": "O(N)"},
        "edge_cases": [
            "Boundary values (minimum and maximum constraints).",
            "Negative numbers and zero in the input.",
            "Duplicate values or repeated elements.",
            "Input already sorted in ascending or descending order.",
            "Single element or two-element inputs."
        ],
    },

    "time_limit_exceeded": {
        "error_type": "Time Limit Exceeded",
        "explanation": (
            "Your code produced correct logic but is too slow for the given "
            "constraints. The current approach has a higher time complexity "
            "than required. You need to optimize your algorithm — often by "
            "replacing nested loops with hash maps, sorting, or binary search."
        ),
        "hint": (
            "Identify the bottleneck loop in your code. Can you replace a "
            "linear search with a hash map lookup (O(1))? Can you sort the "
            "data first and use two pointers or binary search? Think about "
            "reducing the number of operations per element."
        ),
        "review": (
            "The algorithm correctness seems fine, but the time complexity is "
            "too high for the input constraints. Consider using more efficient "
            "data structures (hash maps, heaps, segment trees) or algorithmic "
            "techniques (divide and conquer, sliding window, dynamic programming)."
        ),
        "complexity": {"time": "O(N²) → optimize to O(N log N) or O(N)", "space": "O(N)"},
        "edge_cases": [
            "Maximum constraint inputs (N = 10⁵ or 10⁶).",
            "Worst-case ordering for your algorithm.",
            "Dense graphs or fully connected test cases.",
            "Repeated elements that cause worst-case hash collisions.",
            "Inputs designed to trigger O(N²) behavior."
        ],
    },

    "memory_limit_exceeded": {
        "error_type": "Memory Limit Exceeded",
        "explanation": (
            "Your code used more memory than the limit allowed. This usually happens "
            "due to deep recursion causing a stack overflow, creating extremely large "
            "arrays, or storing unnecessary data in memory."
        ),
        "hint": (
            "Consider using an iterative approach instead of recursion to save stack space. "
            "Check if you can optimize your data structures or perform operations in-place."
        ),
        "review": (
            "The memory usage of your approach is too high. Look for ways to reduce spatial overhead."
        ),
        "complexity": {"time": "—", "space": "—"},
        "edge_cases": [
            "Input size reaching the maximum limit.",
            "Deep recursive call trees.",
            "Creation of large multi-dimensional arrays."
        ],
    },

    "accepted": {
        "error_type": None,
        "explanation": (
            "Congratulations! Your solution was accepted. It successfully passes all test cases "
            "within the time and memory limits."
        ),
        "hint": (
            "Great job! Try to see if you can implement the solution in a different way, "
            "or optimize the existing code for better readability."
        ),
        "review": (
            "Your implementation is correct. Review your variable naming and ensure there "
            "are no redundant checks."
        ),
        "complexity": {"time": "O(N)", "space": "O(N)"},
        "edge_cases": [
            "Empty or null inputs.",
            "Single element inputs.",
            "Maximum input constraints."
        ],
    },
}

# Keep success as an alias to accepted for backward compatibility
MENTOR_RESPONSES["success"] = MENTOR_RESPONSES["accepted"]


# ──────────────────────────────────────────────────────────────
# Abstract Base Provider
# ──────────────────────────────────────────────────────────────

class BaseAIProvider(ABC):
    """Abstract base class defining the interface for all AI operations."""

    @abstractmethod
    def get_mentor_feedback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured mentor feedback.

        Args:
            context: Dictionary containing student execution/submission state.

        Returns:
            Dict conforming to the standardized mentor feedback JSON schema.
        """
        pass

    @abstractmethod
    def ask_question(
        self,
        problem_title: str,
        problem_desc: str,
        code: str,
        language: str,
        user_query: str,
        chat_history: List[Dict[str, str]]
    ) -> str:
        """Handle a direct chat question from a student.

        Args:
            problem_title: Title of the coding problem.
            problem_desc: Description of the problem.
            code: Current editor code.
            language: Programming language.
            user_query: Student's query.
            chat_history: List of previous chat messages.

        Returns:
            AI response string.
        """
        pass

    @abstractmethod
    def solve_problem(self, question: str, technique: str, language: str) -> Dict[str, Any]:
        """Generate a structured JSON solution to a given problem.
        
        Args:
            question: The problem statement.
            technique: The specific technique to use (optional).
            language: The programming language to use.
            
        Returns:
            Dict containing the structured problem solution.
        """
        pass


# ──────────────────────────────────────────────────────────────
# Concrete Provider Implementations
# ──────────────────────────────────────────────────────────────

class DummyProvider(BaseAIProvider):
    """Dummy AI Provider returning mock/static responses for testing and backward compatibility."""

    def get_mentor_feedback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        language = context.get("language", "python").lower()
        execution_status = context.get("execution_status", "")
        compiler_output = context.get("compiler_output", "")
        action_type = context.get("action_type", "run")

        category = _classify_status(execution_status, compiler_output, action_type)
        template = MENTOR_RESPONSES.get(category, MENTOR_RESPONSES["success"])

        return {
            "status": "success",
            "error_type": template["error_type"],
            "explanation": template["explanation"],
            "hint": template["hint"],
            "review": template["review"],
            "complexity": template["complexity"],
            "edge_cases": template["edge_cases"],
            "optimized_code": ""
        }

    def ask_question(
        self,
        problem_title: str,
        problem_desc: str,
        code: str,
        language: str,
        user_query: str,
        chat_history: List[Dict[str, str]]
    ) -> str:
        return (
            f"Hello! I am the Dummy SolvePilot AI mentor. You asked about the problem "
            f"'{problem_title}' written in {language}.\n\n"
            f"Here is your code:\n```\n{code}\n```\n"
            f"And your question: \"{user_query}\"\n\n"
            f"This is a placeholder response. To enable real AI responses, configure the Groq provider."
        )

    def solve_problem(self, question: str, technique: str, language: str) -> Dict[str, Any]:
        return {
            "classification": "Dummy Classification",
            "key_observation": "This is a placeholder observation.",
            "approach": "This is a placeholder approach.",
            "complexity": {"time": "O(1)", "space": "O(1)"},
            "implementation": f"print('Dummy solution for {language}')",
            "explanation": "This is a dummy explanation."
        }


class GroqProvider(BaseAIProvider):
    """Groq AI Provider."""

    @staticmethod
    def _extract_json_object(text: str) -> Optional[str]:
        """Extract the first complete top-level JSON object from *text*.

        Uses brace-depth tracking and correctly ignores braces that appear
        inside JSON-quoted strings (handling escaped quotes too).
        This safely handles conversational prefixes/suffixes the model may
        wrap around its JSON output.

        Returns the extracted JSON substring, or None if no complete
        top-level object is found.
        """
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        i = start

        while i < len(text):
            ch = text[i]

            # Inside a quoted string, a backslash means the next character
            # is escaped — skip both so that \" does not end the string
            # and \{ / \} do not affect depth.
            if in_string and ch == "\\":
                i += 2
                continue

            # Unescaped double-quote toggles string state
            if ch == '"':
                in_string = not in_string
                i += 1
                continue

            # Track braces only outside strings
            if not in_string:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start:i + 1]

            i += 1

        return None

    @staticmethod
    def _repair_json_escapes(text: str) -> str:
        """Repair invalid escape sequences inside JSON string values.

        Walks through *text* character-by-character, tracking whether
        the scanner is inside a JSON string (between unescaped double
        quotes).  Inside a string, every backslash is checked:

        • If the next character is a VALID JSON escape target
          (\", \\\\, /, b, f, n, r, t, or u for \\uXXXX), keep both
          the backslash and the target character.
        • If the next character is anything else (commonly ' from C++
          char literals), the backslash is DROPPED and only the
          following character is kept.

        Outside of JSON strings the text is passed through unchanged.
        This approach is safe for embedded C++ code because it only
        modifies characters inside JSON string values and never touches
        structural JSON syntax.
        """
        # The set of characters that may legally follow a backslash
        # inside a JSON string, per RFC 8259 §7.
        VALID_ESCAPE_CHARS = frozenset('"\\bfnrtu/')

        result = []
        in_string = False
        i = 0
        length = len(text)

        while i < length:
            ch = text[i]

            if not in_string:
                # Outside a JSON string — pass through unchanged
                result.append(ch)
                if ch == '"':
                    in_string = True
                i += 1
            else:
                # Inside a JSON string
                if ch == '\\':
                    if i + 1 < length:
                        next_ch = text[i + 1]
                        if next_ch in VALID_ESCAPE_CHARS:
                            # Valid escape — keep backslash + target
                            result.append(ch)
                            result.append(next_ch)
                            i += 2
                            # For \uXXXX, also copy the four hex digits
                            if next_ch == 'u':
                                hex_end = min(i + 4, length)
                                while i < hex_end:
                                    result.append(text[i])
                                    i += 1
                        else:
                            # INVALID escape (e.g. \' from C++ code) —
                            # drop the backslash, keep the character
                            result.append(next_ch)
                            i += 2
                    else:
                        # Trailing lone backslash at end of input — drop it
                        i += 1
                elif ch == '"':
                    # Unescaped quote ends the string
                    result.append(ch)
                    in_string = False
                    i += 1
                else:
                    result.append(ch)
                    i += 1

        return "".join(result)

    def _execute_json_completion(self, messages: List[Dict[str, str]], max_tokens: int, temperature: float = 0.2, is_retry: bool = False) -> Dict[str, Any]:
        """Execute chat completion, sanitize raw text, parse JSON, and handle retries.

        Pipeline:
            Raw Response → Trim whitespace → Remove markdown fences
            → Extract first complete JSON object → Repair malformed
            escape sequences → json.loads() → [retry on failure]
        """
        try:
            completion = groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            raw_response = completion.choices[0].message.content

            # ── Sanitization Pipeline ──

            # Step 1: Trim leading/trailing whitespace
            sanitized = raw_response.strip()

            # Step 2: Remove markdown code fences (```json ... ``` or ``` ... ```)
            if sanitized.startswith("```"):
                sanitized = re.sub(r"^```[a-zA-Z]*\n", "", sanitized)
            if sanitized.endswith("```"):
                sanitized = sanitized[:-3].strip()

            # Step 3: Extract the first complete JSON object using
            #         brace-depth tracking.  This strips any
            #         conversational prefix/suffix text the model may
            #         have wrapped around the JSON.
            extracted = self._extract_json_object(sanitized)
            extracted_text = extracted if extracted is not None else sanitized

            # Step 4: Repair malformed escape sequences inside JSON
            #         string values (e.g. \' → ', \x → x for any
            #         non-JSON-spec escape character).
            repaired = self._repair_json_escapes(extracted_text)

            # Step 5: Attempt JSON parsing
            try:
                return json.loads(repaired)
            except json.JSONDecodeError as parse_error:
                # ── Diagnostic logging ──
                error_pos = parse_error.pos or 0
                context_start = max(0, error_pos - 50)
                context_end = min(len(repaired), error_pos + 50)
                surrounding = repaired[context_start:context_end]

                logger.error("=" * 80)
                logger.error("JSON PARSE FAILURE — diagnostic dump")
                logger.error("=" * 80)
                logger.error("RAW MODEL RESPONSE:\n%s", raw_response)
                logger.error("-" * 40)
                logger.error("EXTRACTED JSON:\n%s", extracted_text)
                logger.error("-" * 40)
                logger.error("REPAIRED JSON:\n%s", repaired)
                logger.error("-" * 40)
                logger.error(
                    "JSONDecodeError: %s  (char offset %d)",
                    parse_error.msg, error_pos
                )
                logger.error(
                    "Context (±50 chars around offset %d):\n...%s...",
                    error_pos, surrounding
                )
                logger.error("=" * 80)

                if not is_retry:
                    logger.info("Retrying model once with strict JSON instruction...")
                    retry_messages = messages.copy()
                    retry_messages.append({
                        "role": "user",
                        "content": (
                            "CRITICAL: The previous response failed JSON validation. "
                            "Return ONLY a single valid JSON object. "
                            "Do not use markdown wrappers like ```json. "
                            "Do not escape single quotes (\\') — that is invalid JSON. "
                            "Only use escapes defined by the JSON specification: "
                            '\\"  \\\\  \\/  \\b  \\f  \\n  \\r  \\t  \\uXXXX'
                        )
                    })
                    return self._execute_json_completion(retry_messages, max_tokens, temperature, is_retry=True)
                else:
                    logger.error("JSON Parsing failed after retry — returning fallback.")
                    return {
                        "error_type": "Internal Error",
                        "explanation": "The AI service encountered an internal formatting error after multiple attempts.",
                        "hint": "Try regenerating the solution or modifying your request slightly.",
                        "review": "N/A",
                        "complexity": {"time": "N/A", "space": "N/A"},
                        "edge_cases": [],
                        "optimized_code": "",
                        "classification": "Internal Error",
                        "key_observation": "Formatting failure.",
                        "approach": "Parsing failed.",
                        "implementation": "",
                        "steps": [],
                        "implementation_notes": ""
                    }
        except Exception as e:
            logger.error(f"API Error in _execute_json_completion: {e}")
            return {
                "error_type": "Internal API Error",
                "explanation": f"API request failed: {str(e)}",
                "classification": "Internal Error",
                "implementation": ""
            }

    def get_mentor_feedback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not groq_client:
            raise RuntimeError("Groq client is not initialized.")

        # Build prompt messages dynamically using PromptBuilder
        system_prompt = PromptBuilder.build_mentor_system_prompt(context)
        user_prompt = PromptBuilder.build_mentor_user_prompt(context)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response_data = self._execute_json_completion(messages, max_tokens=2000, temperature=0.2)

        # Reconstruct standardized schema response
        return {
            "status": "success",
            "error_type": response_data.get("error_type"),
            "explanation": response_data.get("explanation"),
            "hint": response_data.get("hint"),
            "review": response_data.get("review"),
            "complexity": response_data.get("complexity", {"time": "—", "space": "—"}),
            "edge_cases": response_data.get("edge_cases", []),
            "optimized_code": response_data.get("optimized_code", "")
        }

    def ask_question(
        self,
        problem_title: str,
        problem_desc: str,
        code: str,
        language: str,
        user_query: str,
        chat_history: List[Dict[str, str]]
    ) -> str:
        if not groq_client:
            raise RuntimeError("Groq client is not initialized.")

        # Build prompt messages dynamically using PromptBuilder
        system_prompt = PromptBuilder.build_chat_system_prompt(problem_title, problem_desc)
        user_prompt = PromptBuilder.build_chat_user_prompt(code, language, user_query)

        messages = [{"role": "system", "content": system_prompt}]

        # Add historical messages (max last 10)
        for msg in chat_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current user message
        messages.append({"role": "user", "content": user_prompt})

        completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        return completion.choices[0].message.content

    def solve_problem(self, question: str, technique: str, language: str) -> Dict[str, Any]:
        if not groq_client:
            raise RuntimeError("Groq client is not initialized.")

        return self._solve_with_pipeline(question, technique, language)

    def _solve_with_pipeline(self, question: str, technique: str, language: str) -> Dict[str, Any]:
        """Run the experimental planner-to-generator flow with a single-call fallback."""
        started_at = perf_counter()
        problem_id = hashlib.sha256(question.encode("utf-8")).hexdigest()[:12]
        planner_algorithm = "unavailable"
        generator_algorithm = "unavailable"
        fallback_used = False

        try:
            try:
                plan = self._plan_problem(question)
                planner_algorithm = plan["algorithm"]
            except Exception:
                fallback_used = True
                solution = self._solve_problem_single_call(question, technique, language)
                generator_algorithm = solution.get("approach", "unavailable")
                return solution

            solution = self._generate_solution(question, plan, language)
            generator_algorithm = solution.get("approach", "unavailable")
            return solution
        finally:
            logger.info(
                "solve_benchmark %s",
                json.dumps({
                    "problem_id": problem_id,
                    "planner_algorithm": planner_algorithm,
                    "generator_algorithm": generator_algorithm,
                    "fallback_used": fallback_used,
                    "latency_ms": round((perf_counter() - started_at) * 1000, 2),
                }),
            )

    def _plan_problem(self, question: str) -> Dict[str, Any]:
        """Request and minimally validate the planner's structured algorithm plan."""
        messages = [
            {"role": "system", "content": PromptBuilder.build_planner_system_prompt()},
            {"role": "user", "content": PromptBuilder.build_planner_user_prompt(question)},
        ]
        plan = self._execute_json_completion(messages, max_tokens=2000, temperature=0.2)
        self._validate_plan(plan)
        return plan

    def _generate_solution(self, question: str, plan: Dict[str, Any], language: str) -> Dict[str, Any]:
        """Generate the existing solution JSON from the original problem and plan."""
        messages = [
            {"role": "system", "content": PromptBuilder.build_generator_system_prompt()},
            {"role": "user", "content": PromptBuilder.build_generator_user_prompt(question, plan, language)},
        ]
        return self._execute_json_completion(messages, max_tokens=4000, temperature=0.2)

    def _solve_problem_single_call(self, question: str, technique: str, language: str) -> Dict[str, Any]:
        """Execute the original single-call solver used when planning is unavailable."""
        system_prompt = PromptBuilder.build_solver_system_prompt()
        user_prompt = PromptBuilder.build_solver_user_prompt(question, technique, language)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return self._execute_json_completion(messages, max_tokens=4000, temperature=0.2)

    @staticmethod
    def _validate_plan(plan: Dict[str, Any]) -> None:
        """Reject malformed plans so the request can use the existing solver instead."""
        required_text_fields = ("classification", "key_observation", "algorithm", "implementation_notes")
        if not isinstance(plan, dict):
            raise ValueError("Planner response must be a JSON object.")
        if any(not isinstance(plan.get(field), str) or not plan[field].strip() for field in required_text_fields):
            raise ValueError("Planner response is missing required text fields.")
        if not isinstance(plan.get("steps"), list) or not plan["steps"]:
            raise ValueError("Planner response is missing algorithm steps.")

        complexity = plan.get("complexity")
        if (
            not isinstance(complexity, dict)
            or not isinstance(complexity.get("time"), str)
            or not complexity["time"].strip()
            or not isinstance(complexity.get("space"), str)
            or not complexity["space"].strip()
        ):
            raise ValueError("Planner response is missing complexity information.")


class GeminiProvider(BaseAIProvider):
    """Gemini AI Provider (Placeholder)."""

    def get_mentor_feedback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Generate the prompts to demonstrate PromptBuilder usage
        system_prompt = PromptBuilder.build_mentor_system_prompt(context)
        user_prompt = PromptBuilder.build_mentor_user_prompt(context)

        # Return dummy feedback for now (placeholder implementation)
        return DummyProvider().get_mentor_feedback(context)

    def ask_question(
        self,
        problem_title: str,
        problem_desc: str,
        code: str,
        language: str,
        user_query: str,
        chat_history: List[Dict[str, str]]
    ) -> str:
        return (
            f"[Gemini Provider Placeholder]\n"
            f"Hello! I am the Gemini SolvePilot AI mentor placeholder.\n"
            f"Problem: '{problem_title}'\n"
            f"Question: '{user_query}'"
        )

    def solve_problem(self, question: str, technique: str, language: str) -> Dict[str, Any]:
        return DummyProvider().solve_problem(question, technique, language)


class OpenAIProvider(BaseAIProvider):
    """OpenAI AI Provider (Placeholder)."""

    def get_mentor_feedback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Generate the prompts to demonstrate PromptBuilder usage
        system_prompt = PromptBuilder.build_mentor_system_prompt(context)
        user_prompt = PromptBuilder.build_mentor_user_prompt(context)

        # Return dummy feedback for now (placeholder implementation)
        return DummyProvider().get_mentor_feedback(context)

    def ask_question(
        self,
        problem_title: str,
        problem_desc: str,
        code: str,
        language: str,
        user_query: str,
        chat_history: List[Dict[str, str]]
    ) -> str:
        return (
            f"[OpenAI Provider Placeholder]\n"
            f"Hello! I am the OpenAI SolvePilot AI mentor placeholder.\n"
            f"Problem: '{problem_title}'\n"
            f"Question: '{user_query}'"
        )

    def solve_problem(self, question: str, technique: str, language: str) -> Dict[str, Any]:
        return DummyProvider().solve_problem(question, technique, language)


# ──────────────────────────────────────────────────────────────
# AIService Single Entry Point
# ──────────────────────────────────────────────────────────────

class AIService:
    """Single entry point for all AI operations.

    Coordinates provider-independent operations by delegating tasks to
    the configured AI provider.
    """

    def __init__(self, provider_name: Optional[str] = None):
        if not provider_name:
            # Load provider from environment variable, default to 'groq'
            provider_name = os.getenv("AI_PROVIDER", "groq").lower()

        self.provider_name = provider_name
        self.provider = self._get_provider(provider_name)

    def _get_provider(self, provider_name: str) -> BaseAIProvider:
        providers = {
            "dummy": DummyProvider,
            "groq": GroqProvider,
            "gemini": GeminiProvider,
            "openai": OpenAIProvider
        }

        provider_cls = providers.get(provider_name)
        if not provider_cls:
            # Fallback to dummy if provider not found
            return DummyProvider()

        return provider_cls()

    def get_mentor_feedback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured feedback for student's execution context.

        Args:
            context: Raw submission/execution state details.

        Returns:
            Dict containing feedback keys: error_type, explanation, hint,
            review, complexity, edge_cases, optimized_code.
        """
        response_payload = self.provider.get_mentor_feedback(context)

        execution_status = context.get("execution_status", "")
        compiler_output = context.get("compiler_output", "")
        action_type = context.get("action_type", "run")

        category = _classify_status(execution_status, compiler_output, action_type)

        # Ensure optimized_code is at least present as an empty string if completely missing
        if "optimized_code" not in response_payload or response_payload["optimized_code"] is None:
            response_payload["optimized_code"] = ""

        return response_payload

    def ask_question(
        self,
        problem_title: str,
        problem_desc: str,
        code: str,
        language: str,
        user_query: str,
        chat_history: List[Dict[str, str]]
    ) -> str:
        """Handle chatbot query.

        Args:
            problem_title: Title of the problem.
            problem_desc: Description/statement of the problem.
            code: Student's code in editor.
            language: Programming language.
            user_query: Student's question text.
            chat_history: Previous message history.

        Returns:
            AI response string.
        """
        return self.provider.ask_question(
            problem_title=problem_title,
            problem_desc=problem_desc,
            code=code,
            language=language,
            user_query=user_query,
            chat_history=chat_history
        )

    def solve_problem(self, question: str, technique: str, language: str) -> Dict[str, Any]:
        """Delegate solving a problem to the active provider."""
        return self.provider.solve_problem(question, technique, language)
