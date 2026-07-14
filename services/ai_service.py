import os
import json
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from services.prompt_builder import PromptBuilder


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
        'time_limit_exceeded', 'success'
    """
    s = (execution_status or "").lower().strip()

    if s in ("compilation error",):
        return "compilation_error"
    if s in ("runtime error",):
        return "runtime_error"
    if s in ("rejected", "wrong answer"):
        return "wrong_answer"
    if "time" in s and ("limit" in s or "exceeded" in s):
        return "time_limit_exceeded"
    if s in ("accepted", "success"):
        return "success"

    # Fallback heuristic: check stderr content
    stderr = (compiler_output or "").lower()
    if "error" in stderr and ("compile" in stderr or "syntax" in stderr):
        return "compilation_error"
    if "error" in stderr:
        return "runtime_error"

    return "success"


OPTIMIZED_CODE_SNIPPETS = {
    "python": """def twoSum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []""",

    "cpp": """#include <vector>
#include <unordered_map>

class Solution {
public:
    std::vector<int> twoSum(std::vector<int>& nums, int target) {
        std::unordered_map<int, int> seen;
        for (int i = 0; i < nums.size(); ++i) {
            int complement = target - nums[i];
            if (seen.count(complement)) {
                return {seen[complement], i};
            }
            seen[nums[i]] = i;
        }
        return {};
    }
};""",

    "java": """import java.util.HashMap;
import java.util.Map;

class Solution {
    public int[] twoSum(int[] nums, int target) {
        Map<Integer, Integer> seen = new HashMap<>();
        for (int i = 0; i < nums.length; i++) {
            int complement = target - nums[i];
            if (seen.containsKey(complement)) {
                return new int[] { seen.get(complement), i };
            }
            seen.put(nums[i], i);
        }
        return new int[] {};
    }
}""",

    "javascript": """function twoSum(nums, target) {
    const seen = new Map();
    for (let i = 0; i < nums.length; i++) {
        const complement = target - nums[i];
        if (seen.has(complement)) {
            return [seen.get(complement), i];
        }
        seen.set(nums[i], i);
    }
    return [];
}"""
}


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

    "success": {
        "error_type": None,
        "explanation": (
            "The approach uses a Hash Map to store each number's complement "
            "as we iterate through the array. For every element, we check "
            "whether its complement (target − current) already exists in the "
            "map, giving us an O(N) lookup instead of a nested loop."
        ),
        "hint": (
            "Think about what value you need to find for each element to "
            "reach the target. Store the numbers you've already seen in a "
            "data structure that supports O(1) lookup, and check the "
            "complement on each iteration."
        ),
        "review": (
            "Your implementation correctly uses a hash-based approach. "
            "Consider adding an early return if the input array has fewer "
            "than two elements, and make sure duplicate values are handled "
            "properly (the map stores the latest index for each value)."
        ),
        "complexity": {"time": "O(N)", "space": "O(N)"},
        "edge_cases": [
            "Input array with fewer than 2 elements.",
            "Array containing negative numbers and zero.",
            "No valid pair sums to the target.",
            "Duplicate values present in the array.",
            "Very large input approaching constraint limits."
        ],
    },
}


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
            "optimized_code": OPTIMIZED_CODE_SNIPPETS.get(
                language, OPTIMIZED_CODE_SNIPPETS["python"]
            )
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


class GroqProvider(BaseAIProvider):
    """Groq AI Provider."""

    def get_mentor_feedback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not groq_client:
            raise RuntimeError("Groq client is not initialized.")

        # Build prompt messages dynamically using PromptBuilder
        system_prompt = PromptBuilder.build_mentor_system_prompt()
        user_prompt = PromptBuilder.build_mentor_user_prompt(context)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=2000
        )

        raw_response = completion.choices[0].message.content
        response_data = json.loads(raw_response)

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
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        return completion.choices[0].message.content


class GeminiProvider(BaseAIProvider):
    """Gemini AI Provider (Placeholder)."""

    def get_mentor_feedback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Generate the prompts to demonstrate PromptBuilder usage
        system_prompt = PromptBuilder.build_mentor_system_prompt()
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


class OpenAIProvider(BaseAIProvider):
    """OpenAI AI Provider (Placeholder)."""

    def get_mentor_feedback(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Generate the prompts to demonstrate PromptBuilder usage
        system_prompt = PromptBuilder.build_mentor_system_prompt()
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
            # Load provider from environment variable, default to 'dummy'
            provider_name = os.getenv("AI_PROVIDER", "dummy").lower()

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
        return self.provider.get_mentor_feedback(context)

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
