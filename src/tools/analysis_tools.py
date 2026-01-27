"""
Analysis Tools - Static analysis tools for code quality assessment

Provides analysis capabilities for the Auditor agent.
"""

from typing import Dict
from src.tools.refactoring_tools import RefactoringTools


# Global tools instance
_tools = None


def _get_tools() -> RefactoringTools:
    """Get or create the global tools instance."""
    global _tools
    if _tools is None:
        _tools = RefactoringTools(base_sandbox="./sandbox")
    return _tools


def run_pylint(file_path: str) -> Dict:
    """
    Run pylint analysis on a file.

    Args:
        file_path: Path to the Python file (relative to sandbox)

    Returns:
        Dictionary containing:
            - score: Pylint score (0-10)
            - total_issues: Total number of issues
            - errors: List of errors found
            - warnings: List of warnings
            - conventions: List of convention violations
            - refactors: List of refactoring suggestions
            - summary: Human-readable summary
            - raw_output: Full pylint output

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file is outside sandbox
    """
    tools = _get_tools()
    result = tools.run_pylint(file_path)

    if not result["success"]:
        if "outside sandbox" in result.get("error", ""):
            raise PermissionError(result["error"])
        raise FileNotFoundError(result["error"])

    # Return the result as-is (already structured for LLM consumption)
    return result
