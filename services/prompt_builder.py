from typing import Dict, Any, List

# ──────────────────────────────────────────────────────────────
# Centralized Prompt Templates
# ──────────────────────────────────────────────────────────────

MENTOR_SYSTEM_TEMPLATE = """You are 'SolvePilot AI Mentor', an expert software engineer and supportive coding coach. Your objective is to help students learn how to debug and solve programming challenges.

Operational Guidelines:
1. Be encouraging, helpful, and professional.
2. DO NOT output the full solution code immediately. If the code has errors or logic mismatches, explain the mistake conceptually and guide them using clues or progressive hints.
3. Review the student's implementation for code quality, efficiency, readability, and correct approach.
4. Provide a Big-O asymptotic analysis of their time and space complexity.
5. List at least 3-4 edge cases they should keep in mind for this problem.

Response Format:
You MUST respond with a single, valid JSON object matching the following structure:
{
  "error_type": "string or null. Specify category (e.g. 'Compilation Error', 'Runtime Error', 'Wrong Answer', 'Time Limit Exceeded') or null if successful.",
  "explanation": "string. Explain why their current execution status occurred or why the compiler failed.",
  "hint": "string. A helpful clue or guided question to help them fix their code without giving the answer.",
  "review": "string. Review of their code quality, naming conventions, redundancy, or logic.",
  "complexity": {
    "time": "string. Expected time complexity (e.g. 'O(N)', 'O(1)').",
    "space": "string. Expected space complexity (e.g. 'O(N)', 'O(N log N)')."
  },
  "edge_cases": [
    "string. A list of important edge cases they should test or consider."
  ],
  "optimized_code": "string. An optimized reference implementation in the student's programming language."
}

Do not include any prefix text, markdown block wraps (like ```json), or suffix outside of the JSON object.
"""

MENTOR_USER_TEMPLATE = """Analyze the following student coding execution/submission context and generate the structured JSON feedback.

[PROBLEM & CONTEXT]
Problem Title: {problem_title}
Problem Statement: {problem_statement}
Programming Language: {language}

[STUDENT CODE]
```
{code}
```

[EXECUTION METADATA]
Action Type: {action_type}
Execution/Submission Status: {execution_status}
Verdict Message: {message}

[COMPILER & RUNTIME OUTPUTS]
Stdin Input: {stdin}
Compiler Output (Stderr): {compiler_output}
Runtime Output (Stdout): {runtime_output}

[TEST CASE DIFFERENCES]
Expected Output: {expected_output}
Actual Output: {actual_output}
"""

CHAT_SYSTEM_TEMPLATE = """You are 'SolvePilot AI', an expert coding mentor. Your goal is to help students learn and improve.

CAPABILITIES:
- Provide HINTS and EXPLANATIONS for logic issues.
- Provide LINE-BY-LINE EXPLANATIONS of code if requested.
- Suggest BETTER/OPTIMIZED SOLUTIONS if the student asks for improvements.
- Identify syntax or logical errors clearly.

CONTEXT:
Problem Title: {problem_title}
Problem Description: {problem_desc}

GUIDELINES:
- Be encouraging and helpful.
- DO NOT just give the full solution immediately unless they are very stuck; prioritize teaching.
- Use Markdown for code snippets and formatting.
- Keep responses focused and readable.
"""

CHAT_USER_TEMPLATE = """STUDENT'S CURRENT CODE ({language}):
```
{code}
```

STUDENT'S QUESTION:
{user_query}"""


# ──────────────────────────────────────────────────────────────
# PromptBuilder Class
# ──────────────────────────────────────────────────────────────

class PromptBuilder:
    """Class responsible for generating structured and formatted prompts for AI providers.

    Centralizes all prompt templates and provides helper methods to build payloads
    from raw context data.
    """

    @staticmethod
    def build_mentor_system_prompt() -> str:
        """Get the system prompt for the AI Mentor feedback session."""
        return MENTOR_SYSTEM_TEMPLATE

    @staticmethod
    def build_mentor_user_prompt(context: Dict[str, Any]) -> str:
        """Format the user session context details into the AI Mentor user prompt."""
        # Sanitize and get defaults for context dictionary keys
        problem_title = context.get("problem_title", "Unknown Problem")
        problem_statement = context.get("problem_statement", "No description available.")
        language = context.get("language", "python")
        code = context.get("code", "")
        action_type = context.get("action_type", "run")
        execution_status = context.get("execution_status", "unknown")
        message = context.get("message", "")
        stdin = context.get("stdin", "N/A")
        compiler_output = context.get("compiler_output", "")
        runtime_output = context.get("runtime_output", "")
        expected_output = context.get("expected_output", "")
        actual_output = context.get("actual_output", "")

        return MENTOR_USER_TEMPLATE.format(
            problem_title=problem_title,
            problem_statement=problem_statement,
            language=language,
            code=code,
            action_type=action_type,
            execution_status=execution_status,
            message=message,
            stdin=stdin,
            compiler_output=compiler_output,
            runtime_output=runtime_output,
            expected_output=expected_output,
            actual_output=actual_output
        )

    @staticmethod
    def build_chat_system_prompt(problem_title: str, problem_desc: str) -> str:
        """Format and return the system instructions for the direct chatbot."""
        return CHAT_SYSTEM_TEMPLATE.format(
            problem_title=problem_title,
            problem_desc=problem_desc
        )

    @staticmethod
    def build_chat_user_prompt(code: str, language: str, user_query: str) -> str:
        """Format and return the user question details for the chatbot."""
        return CHAT_USER_TEMPLATE.format(
            language=language,
            code=code,
            user_query=user_query
        )
