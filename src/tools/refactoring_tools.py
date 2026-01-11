"""
Refactoring Tools - The "Hands and Eyes" of The Refactoring Swarm

This module provides the Internal API for agents (Auditor, Fixer, Judge)
to safely interact with code files in the sandbox environment.

Security: All file operations are restricted to the sandbox directory.
"""

import subprocess
import os
import shutil
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any
from datetime import datetime
from src.utils.logger import log_experiment, ActionType


class RefactoringTools:
    """
    Toolbox for the Refactoring Swarm agents.

    Provides secure file operations, static analysis, and testing capabilities
    while enforcing sandbox security boundaries.
    """

    def __init__(self, base_sandbox: str = "./sandbox"):
        """
        Initialize the RefactoringTools with a secure sandbox.

        Args:
            base_sandbox: Path to the sandbox directory (default: "./sandbox")
        """
        self.sandbox_path = Path(base_sandbox).resolve()
        self.backup_dir = self.sandbox_path / ".backups"

        # Ensure sandbox exists
        if not self.sandbox_path.exists():
            self.sandbox_path.mkdir(parents=True, exist_ok=True)

        # Ensure backup directory exists
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)

    # ==================== SECURITY LAYER ====================

    def _safe_path(self, target_path: str) -> Path:
        """
        Validates that a file path is within the sandbox boundary.

        This is the SECURITY GUARD that prevents agents from accessing
        or modifying files outside the sandbox.

        Args:
            target_path: The path to validate

        Returns:
            Resolved Path object if safe

        Raises:
            PermissionError: If path is outside the sandbox
        """
        # Handle both absolute and relative paths
        if not Path(target_path).is_absolute():
            full_path = (self.sandbox_path / target_path).resolve()
        else:
            full_path = Path(target_path).resolve()

        # Check if the resolved path is within sandbox
        try:
            full_path.relative_to(self.sandbox_path)
        except ValueError:
            raise PermissionError(
                f"🚫 SECURITY VIOLATION: Access denied to '{target_path}'\n"
                f"   Reason: Path is outside the sandbox boundary.\n"
                f"   Sandbox: {self.sandbox_path}\n"
                f"   Attempted: {full_path}"
            )

        return full_path

    # ==================== AUDITOR TOOLS (Read-Only) ====================

    def read_file(self, file_name: str) -> Dict[str, Any]:
        """
        Reads the content of a file in the sandbox.

        This is the Auditor's "eyes" - allows reading code for analysis.

        Args:
            file_name: Path to the file (relative to sandbox or absolute within sandbox)

        Returns:
            Dictionary with:
                - success (bool): Whether the operation succeeded
                - content (str): File content if successful
                - error (str): Error message if failed
                - path (str): Actual file path used
        """
        try:
            safe_path = self._safe_path(file_name)

            if not safe_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_name}",
                    "content": None,
                    "path": str(safe_path)
                }

            if not safe_path.is_file():
                return {
                    "success": False,
                    "error": f"Path is not a file: {file_name}",
                    "content": None,
                    "path": str(safe_path)
                }

            with open(safe_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                "success": True,
                "content": content,
                "error": None,
                "path": str(safe_path),
                "size_bytes": len(content.encode('utf-8')),
                "lines": len(content.splitlines())
            }

        except PermissionError as e:
            return {
                "success": False,
                "error": str(e),
                "content": None,
                "path": file_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error reading file: {str(e)}",
                "content": None,
                "path": file_name
            }

    def list_files(self, pattern: str = "*.py") -> Dict[str, Any]:
        """
        Lists all files in the sandbox matching a pattern.

        Helps agents discover what files are available for refactoring.

        Args:
            pattern: Glob pattern for file matching (default: "*.py")

        Returns:
            Dictionary with:
                - success (bool): Whether the operation succeeded
                - files (list): List of relative file paths
                - count (int): Number of files found
        """
        try:
            files = list(self.sandbox_path.glob(f"**/{pattern}"))
            # Convert to relative paths and exclude backup directory
            relative_files = [
                str(f.relative_to(self.sandbox_path))
                for f in files
                if self.backup_dir not in f.parents and f.is_file()
            ]

            return {
                "success": True,
                "files": sorted(relative_files),
                "count": len(relative_files),
                "pattern": pattern
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error listing files: {str(e)}",
                "files": [],
                "count": 0
            }

    def run_pylint(self, file_name: str) -> Dict[str, Any]:
        """
        Runs pylint static analysis on a file.

        This is the Auditor's primary tool for measuring code quality.

        Args:
            file_name: Path to the Python file to analyze

        Returns:
            Dictionary with:
                - success (bool): Whether pylint ran successfully
                - score (float): Pylint score (0-10)
                - raw_output (str): Full pylint output
                - errors (list): List of error dictionaries
                - warnings (list): List of warning dictionaries
                - conventions (list): List of convention violations
                - file_path (str): Path that was analyzed
        """
        try:
            safe_path = self._safe_path(file_name)

            if not safe_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_name}",
                    "score": None,
                    "raw_output": None
                }

            # Run pylint with JSON output format for better parsing
            result = subprocess.run(
                ['pylint', str(safe_path), '--output-format=json'],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parse JSON output
            try:
                issues = json.loads(result.stdout) if result.stdout else []
            except json.JSONDecodeError:
                issues = []

            # Run again with text format to get the score
            result_text = subprocess.run(
                ['pylint', str(safe_path), '--output-format=text'],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Extract score from text output
            score = self._extract_pylint_score(result_text.stdout)

            # Categorize issues
            errors = [i for i in issues if i.get('type') == 'error']
            warnings = [i for i in issues if i.get('type') == 'warning']
            conventions = [i for i in issues if i.get('type') == 'convention']
            refactors = [i for i in issues if i.get('type') == 'refactor']

            return {
                "success": True,
                "score": score,
                "raw_output": result_text.stdout,
                "errors": errors,
                "warnings": warnings,
                "conventions": conventions,
                "refactors": refactors,
                "total_issues": len(issues),
                "file_path": str(safe_path),
                "summary": self._generate_pylint_summary(score, errors, warnings, conventions, refactors)
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Pylint analysis timed out (30s limit)",
                "score": None
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Pylint is not installed. Run: pip install pylint",
                "score": None
            }
        except PermissionError as e:
            return {
                "success": False,
                "error": str(e),
                "score": None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error running pylint: {str(e)}",
                "score": None
            }

    def _extract_pylint_score(self, output: str) -> Optional[float]:
        """Extract the numeric score from pylint text output."""
        for line in output.splitlines():
            if "Your code has been rated at" in line:
                # Example: "Your code has been rated at 7.50/10"
                try:
                    score_str = line.split("rated at")[1].split("/")[0].strip()
                    return float(score_str)
                except (IndexError, ValueError):
                    pass
        return None

    def _generate_pylint_summary(self, score: Optional[float], errors: list,
                                 warnings: list, conventions: list, refactors: list) -> str:
        """Generate a human-readable summary of pylint results."""
        if score is None:
            return "Unable to determine score"

        summary = f"Score: {score}/10\n"
        summary += f"Errors: {len(errors)}, Warnings: {len(warnings)}, "
        summary += f"Conventions: {len(conventions)}, Refactors: {len(refactors)}"

        if score >= 9.0:
            summary += "\n✅ Excellent code quality!"
        elif score >= 7.0:
            summary += "\n✓ Good code quality"
        elif score >= 5.0:
            summary += "\n⚠️ Needs improvement"
        else:
            summary += "\n❌ Poor code quality - significant refactoring needed"

        return summary

    # ==================== FIXER TOOLS (Write Operations) ====================

    def write_file(self, file_name: str, content: str, create_backup: bool = True) -> Dict[str, Any]:
        """
        Writes content to a file in the sandbox.

        This is the Fixer's "hands" - allows modifying code.

        Args:
            file_name: Path to the file (relative to sandbox or absolute within sandbox)
            content: Content to write to the file
            create_backup: Whether to create a backup before overwriting (default: True)

        Returns:
            Dictionary with:
                - success (bool): Whether the operation succeeded
                - path (str): Path that was written
                - backup_path (str): Path to backup if created
                - error (str): Error message if failed
        """
        try:
            safe_path = self._safe_path(file_name)

            backup_path = None

            # Create backup if file exists and backup is requested
            if create_backup and safe_path.exists():
                backup_result = self.create_backup(file_name)
                if backup_result["success"]:
                    backup_path = backup_result["backup_path"]

            # Ensure parent directory exists
            safe_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the content
            with open(safe_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return {
                "success": True,
                "path": str(safe_path),
                "backup_path": backup_path,
                "bytes_written": len(content.encode('utf-8')),
                "lines_written": len(content.splitlines()),
                "error": None
            }

        except PermissionError as e:
            return {
                "success": False,
                "error": str(e),
                "path": file_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error writing file: {str(e)}",
                "path": file_name
            }

    def create_backup(self, file_name: str) -> Dict[str, Any]:
        """
        Creates a timestamped backup of a file.

        Args:
            file_name: Path to the file to backup

        Returns:
            Dictionary with:
                - success (bool): Whether backup was created
                - backup_path (str): Path to the backup file
                - error (str): Error message if failed
        """
        try:
            safe_path = self._safe_path(file_name)

            if not safe_path.exists():
                return {
                    "success": False,
                    "error": f"Cannot backup non-existent file: {file_name}",
                    "backup_path": None
                }

            # Create timestamp-based backup name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{safe_path.stem}_{timestamp}{safe_path.suffix}"
            backup_path = self.backup_dir / backup_name

            # Copy the file
            shutil.copy2(safe_path, backup_path)

            return {
                "success": True,
                "backup_path": str(backup_path),
                "original_path": str(safe_path),
                "timestamp": timestamp,
                "error": None
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error creating backup: {str(e)}",
                "backup_path": None
            }

    def restore_backup(self, backup_path: str, target_file: str) -> Dict[str, Any]:
        """
        Restores a file from a backup.

        Args:
            backup_path: Path to the backup file (in .backups directory)
            target_file: Target file to restore to

        Returns:
            Dictionary with success status and details
        """
        try:
            # Validate backup path is in backup directory
            backup_full = Path(backup_path).resolve()
            if self.backup_dir not in backup_full.parents and backup_full.parent != self.backup_dir:
                return {
                    "success": False,
                    "error": "Backup path must be in the .backups directory"
                }

            if not backup_full.exists():
                return {
                    "success": False,
                    "error": f"Backup file not found: {backup_path}"
                }

            # Validate target path is in sandbox
            target_path = self._safe_path(target_file)

            # Restore the backup
            shutil.copy2(backup_full, target_path)

            return {
                "success": True,
                "restored_to": str(target_path),
                "from_backup": str(backup_full),
                "error": None
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error restoring backup: {str(e)}"
            }

    def list_backups(self) -> Dict[str, Any]:
        """
        Lists all available backups.

        Returns:
            Dictionary with list of backups and their details
        """
        try:
            backups = []
            for backup_file in self.backup_dir.glob("*"):
                if backup_file.is_file():
                    backups.append({
                        "name": backup_file.name,
                        "path": str(backup_file),
                        "size_bytes": backup_file.stat().st_size,
                        "modified": datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
                    })

            return {
                "success": True,
                "backups": sorted(backups, key=lambda x: x["modified"], reverse=True),
                "count": len(backups)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error listing backups: {str(e)}",
                "backups": []
            }

    # ==================== JUDGE TOOLS (Validation) ====================

    def run_pytest(self, target: Optional[str] = None, verbose: bool = True) -> Dict[str, Any]:
        """
        Runs pytest on the sandbox or a specific file/directory.

        This is the Judge's tool for verifying that refactored code still works.

        Args:
            target: Specific file or directory to test (None = entire sandbox)
            verbose: Whether to run pytest in verbose mode

        Returns:
            Dictionary with:
                - success (bool): Whether all tests passed
                - passed (int): Number of passed tests
                - failed (int): Number of failed tests
                - errors (int): Number of errors
                - stdout (str): Standard output from pytest
                - stderr (str): Standard error from pytest
                - detailed_failures (list): Detailed failure information
        """
        try:
            # Determine what to test
            if target is None:
                test_path = self.sandbox_path
            else:
                test_path = self._safe_path(target)
                if not test_path.exists():
                    return {
                        "success": False,
                        "error": f"Test target not found: {target}",
                        "passed": 0,
                        "failed": 0
                    }

            # Build pytest command
            cmd = ['pytest', str(test_path)]
            if verbose:
                cmd.append('-v')
            cmd.extend(['--tb=short', '--no-header'])  # Better output format

            # Run pytest
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.sandbox_path)
            )

            # Parse the output to extract test statistics
            stats = self._parse_pytest_output(result.stdout + result.stderr)

            return {
                "success": result.returncode == 0,
                "passed": stats["passed"],
                "failed": stats["failed"],
                "errors": stats["errors"],
                "skipped": stats["skipped"],
                "total": stats["total"],
                "stdout": result.stdout,
                "stderr": result.stderr,
                "full_output": result.stdout + "\n" + result.stderr,
                "return_code": result.returncode,
                "test_path": str(test_path),
                "summary": self._generate_pytest_summary(stats, result.returncode)
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Pytest execution timed out (60s limit)",
                "passed": 0,
                "failed": 0
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Pytest is not installed. Run: pip install pytest",
                "passed": 0,
                "failed": 0
            }
        except PermissionError as e:
            return {
                "success": False,
                "error": str(e),
                "passed": 0,
                "failed": 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error running pytest: {str(e)}",
                "passed": 0,
                "failed": 0
            }

    def _parse_pytest_output(self, output: str) -> Dict[str, int]:
        """Parse pytest output to extract test statistics."""
        stats = {
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "total": 0
        }

        # Look for pytest summary line
        # Example: "= 3 passed, 1 failed in 0.12s ="
        for line in output.splitlines():
            if " passed" in line or " failed" in line:
                if "passed" in line:
                    try:
                        stats["passed"] = int(line.split()[1])
                    except (IndexError, ValueError):
                        pass
                if "failed" in line:
                    try:
                        # Find the word before "failed"
                        words = line.split()
                        for i, word in enumerate(words):
                            if word == "failed" and i > 0:
                                stats["failed"] = int(words[i-1])
                                break
                    except (IndexError, ValueError):
                        pass
                if "error" in line:
                    try:
                        words = line.split()
                        for i, word in enumerate(words):
                            if "error" in word and i > 0:
                                stats["errors"] = int(words[i-1])
                                break
                    except (IndexError, ValueError):
                        pass

        stats["total"] = stats["passed"] + stats["failed"] + stats["errors"]
        return stats

    def _generate_pytest_summary(self, stats: Dict[str, int], return_code: int) -> str:
        """Generate a human-readable summary of pytest results."""
        if stats["total"] == 0:
            return "⚠️ No tests found or collected"

        summary = f"Total: {stats['total']} tests"
        if stats["passed"] > 0:
            summary += f" | ✅ Passed: {stats['passed']}"
        if stats["failed"] > 0:
            summary += f" | ❌ Failed: {stats['failed']}"
        if stats["errors"] > 0:
            summary += f" | ⚠️ Errors: {stats['errors']}"
        if stats["skipped"] > 0:
            summary += f" | ⏭️ Skipped: {stats['skipped']}"

        if return_code == 0:
            summary += "\n✅ ALL TESTS PASSED!"
        else:
            summary += "\n❌ SOME TESTS FAILED - Review output for details"

        return summary

    # ==================== UTILITY METHODS ====================

    def get_sandbox_info(self) -> Dict[str, Any]:
        """
        Returns information about the sandbox environment.

        Returns:
            Dictionary with sandbox details
        """
        try:
            python_files = list(self.sandbox_path.glob("**/*.py"))
            test_files = [
                f for f in python_files if "test_" in f.name or f.name.endswith("_test.py")]

            return {
                "sandbox_path": str(self.sandbox_path),
                "backup_path": str(self.backup_dir),
                "total_python_files": len(python_files),
                "test_files": len(test_files),
                "backups_available": len(list(self.backup_dir.glob("*"))),
                "exists": self.sandbox_path.exists()
            }
        except Exception as e:
            return {
                "error": f"Error getting sandbox info: {str(e)}"
            }

    def validate_target_dir(self, target_dir: str) -> Dict[str, Any]:
        """
        Validates that a target directory exists and is within sandbox.

        Args:
            target_dir: Directory path to validate

        Returns:
            Dictionary with validation result
        """
        try:
            safe_path = self._safe_path(target_dir)

            if not safe_path.exists():
                return {
                    "valid": False,
                    "error": f"Directory does not exist: {target_dir}",
                    "path": str(safe_path)
                }

            if not safe_path.is_dir():
                return {
                    "valid": False,
                    "error": f"Path is not a directory: {target_dir}",
                    "path": str(safe_path)
                }

            return {
                "valid": True,
                "path": str(safe_path),
                "relative_path": str(safe_path.relative_to(self.sandbox_path))
            }

        except PermissionError as e:
            return {
                "valid": False,
                "error": str(e),
                "path": target_dir
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
                "path": target_dir
            }

