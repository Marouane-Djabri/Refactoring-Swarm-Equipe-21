"""
File Operations - Wrapper around RefactoringTools for file operations

Provides simplified file operations for agents while maintaining sandbox security.
"""

from pathlib import Path
from typing import Optional
from src.tools.refactoring_tools import RefactoringTools


# Global tools instance
_tools = None


def _get_tools() -> RefactoringTools:
    """Get or create the global tools instance."""
    global _tools
    if _tools is None:
        _tools = RefactoringTools(base_sandbox="./sandbox")
    return _tools


def read_file(file_path: str) -> str:
    """
    Read the content of a file.

    Args:
        file_path: Path to the file (relative to sandbox)

    Returns:
        File content as string

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file is outside sandbox
    """
    tools = _get_tools()
    result = tools.read_file(file_path)

    if not result["success"]:
        if "outside sandbox" in result.get("error", ""):
            raise PermissionError(result["error"])
        raise FileNotFoundError(result["error"])

    return result["content"]


def write_file(file_path: str, content: str, create_backup: bool = True) -> None:
    """
    Write content to a file.

    Args:
        file_path: Path to the file (relative to sandbox)
        content: Content to write
        create_backup: Whether to create a backup first

    Raises:
        PermissionError: If file is outside sandbox
    """
    tools = _get_tools()
    result = tools.write_file(file_path, content, create_backup=create_backup)

    if not result["success"]:
        raise PermissionError(result["error"])


def backup_file(file_path: str) -> str:
    """
    Create a backup of a file.

    Args:
        file_path: Path to the file (relative to sandbox)

    Returns:
        Path to the backup file

    Raises:
        PermissionError: If file is outside sandbox
    """
    tools = _get_tools()
    result = tools.create_backup(file_path)

    if not result["success"]:
        raise PermissionError(result["error"])

    return result["backup_path"]


def list_files(target_dir) -> list:
    """
    List Python files in the sandbox.

    Args:
        target_dir: Directory path (for API compatibility, can be Path or str)

    Returns:
        List of file paths matching *.py pattern
    """
    tools = _get_tools()
    result = tools.list_files("**/*.py")

    if not result["success"]:
        return []

    return result["files"]
