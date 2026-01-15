"""
Sandbox Security - Validates file paths to prevent escaping the sandbox

Ensures all file operations stay within the authorized sandbox directory.
"""

from pathlib import Path
from typing import Union


def validate_path(file_path: Union[str, Path]) -> Path:
    """
    Validate that a file path is within the sandbox.

    Args:
        file_path: Path to validate

    Returns:
        Validated Path object

    Raises:
        PermissionError: If path is outside the sandbox
    """
    sandbox_path = Path("./sandbox").resolve()

    # Convert to Path and resolve
    if isinstance(file_path, str):
        file_path = Path(file_path)

    full_path = file_path.resolve() if file_path.is_absolute() else (
        sandbox_path / file_path).resolve()

    # Check if the path is within sandbox
    try:
        full_path.relative_to(sandbox_path)
    except ValueError:
        raise PermissionError(
            f"🚫 SECURITY VIOLATION: Access denied to '{file_path}'\n"
            f"   Reason: Path is outside the sandbox boundary.\n"
            f"   Sandbox: {sandbox_path}\n"
            f"   Attempted: {full_path}"
        )

    return full_path
