"""
Tool Wrapper - Adds Logging and Telemetry to RefactoringTools

This wrapper automatically logs all tool interactions for scientific analysis
and provides a cleaner interface for the agents.
"""

from typing import Dict, Optional, Any
from src.tools.refactoring_tools import RefactoringTools
from src.utils.logger import log_experiment, ActionType


class ToolWrapper:
    """
    High-level wrapper around RefactoringTools that adds automatic logging.

    Use this wrapper in your agents to ensure all tool interactions are
    properly logged for scientific analysis.
    """

    def __init__(self, base_sandbox: str = "./sandbox", enable_logging: bool = True):
        """
        Initialize the tool wrapper.

        Args:
            base_sandbox: Path to the sandbox directory
            enable_logging: Whether to enable automatic logging (default: True)
        """
        self.tools = RefactoringTools(base_sandbox)
        self.enable_logging = enable_logging

    def _log_tool_call(self, agent_name: str, model_used: str, action: ActionType,
                       tool_name: str, input_data: Dict, output_data: Dict):
        """Helper to log tool interactions."""
        if not self.enable_logging:
            return

        try:
            details = {
                "input_prompt": f"Tool: {tool_name}\nInput: {str(input_data)}",
                "output_response": str(output_data),
                "tool_name": tool_name,
                "input": input_data,
                "output": output_data
            }

            status = "SUCCESS" if output_data.get(
                "success", False) else "FAILURE"

            log_experiment(
                agent_name=agent_name,
                model_used=model_used,
                action=action,
                details=details,
                status=status
            )
        except Exception as e:
            # Don't let logging errors break the tool execution
            print(f"⚠️ Warning: Failed to log tool call: {e}")

    # ==================== AUDITOR TOOLS ====================

    def audit_read_file(self, file_name: str, agent_name: str = "Auditor",
                        model_used: str = "unknown") -> Dict[str, Any]:
        """
        Read a file with automatic logging for audit purposes.

        Args:
            file_name: Path to the file to read
            agent_name: Name of the agent calling this tool
            model_used: Model being used by the agent

        Returns:
            Result dictionary from read_file
        """
        result = self.tools.read_file(file_name)

        self._log_tool_call(
            agent_name=agent_name,
            model_used=model_used,
            action=ActionType.ANALYSIS,
            tool_name="read_file",
            input_data={"file_name": file_name},
            output_data=result
        )

        return result

    def audit_run_pylint(self, file_name: str, agent_name: str = "Auditor",
                         model_used: str = "unknown") -> Dict[str, Any]:
        """
        Run pylint analysis with automatic logging.

        Args:
            file_name: Path to the file to analyze
            agent_name: Name of the agent calling this tool
            model_used: Model being used by the agent

        Returns:
            Result dictionary from run_pylint
        """
        result = self.tools.run_pylint(file_name)

        self._log_tool_call(
            agent_name=agent_name,
            model_used=model_used,
            action=ActionType.ANALYSIS,
            tool_name="run_pylint",
            input_data={"file_name": file_name},
            output_data=result
        )

        return result

    def audit_list_files(self, pattern: str = "*.py", agent_name: str = "Auditor",
                         model_used: str = "unknown") -> Dict[str, Any]:
        """
        List files in sandbox with automatic logging.

        Args:
            pattern: Glob pattern for file matching
            agent_name: Name of the agent calling this tool
            model_used: Model being used by the agent

        Returns:
            Result dictionary from list_files
        """
        result = self.tools.list_files(pattern)

        self._log_tool_call(
            agent_name=agent_name,
            model_used=model_used,
            action=ActionType.ANALYSIS,
            tool_name="list_files",
            input_data={"pattern": pattern},
            output_data=result
        )

        return result

    # ==================== FIXER TOOLS ====================

    def fixer_write_file(self, file_name: str, content: str, create_backup: bool = True,
                         agent_name: str = "Fixer", model_used: str = "unknown") -> Dict[str, Any]:
        """
        Write refactored code to a file with automatic logging.

        Args:
            file_name: Path to the file to write
            content: Refactored code content
            create_backup: Whether to create a backup first
            agent_name: Name of the agent calling this tool
            model_used: Model being used by the agent

        Returns:
            Result dictionary from write_file
        """
        result = self.tools.write_file(file_name, content, create_backup)

        self._log_tool_call(
            agent_name=agent_name,
            model_used=model_used,
            action=ActionType.FIX,
            tool_name="write_file",
            input_data={
                "file_name": file_name,
                "content_length": len(content),
                "create_backup": create_backup
            },
            output_data=result
        )

        return result

    def fixer_restore_backup(self, backup_path: str, target_file: str,
                             agent_name: str = "Fixer", model_used: str = "unknown") -> Dict[str, Any]:
        """
        Restore a file from backup with automatic logging.

        Args:
            backup_path: Path to the backup file
            target_file: Target file to restore to
            agent_name: Name of the agent calling this tool
            model_used: Model being used by the agent

        Returns:
            Result dictionary from restore_backup
        """
        result = self.tools.restore_backup(backup_path, target_file)

        self._log_tool_call(
            agent_name=agent_name,
            model_used=model_used,
            action=ActionType.FIX,
            tool_name="restore_backup",
            input_data={"backup_path": backup_path,
                        "target_file": target_file},
            output_data=result
        )

        return result

    # ==================== JUDGE TOOLS ====================

    def judge_run_pytest(self, target: Optional[str] = None, verbose: bool = True,
                         agent_name: str = "Judge", model_used: str = "unknown") -> Dict[str, Any]:
        """
        Run pytest validation with automatic logging.

        Args:
            target: Specific file or directory to test
            verbose: Whether to run in verbose mode
            agent_name: Name of the agent calling this tool
            model_used: Model being used by the agent

        Returns:
            Result dictionary from run_pytest
        """
        result = self.tools.run_pytest(target, verbose)

        self._log_tool_call(
            agent_name=agent_name,
            model_used=model_used,
            action=ActionType.DEBUG if not result.get(
                "success") else ActionType.ANALYSIS,
            tool_name="run_pytest",
            input_data={"target": target, "verbose": verbose},
            output_data=result
        )

        return result

    # ==================== UTILITY METHODS ====================

    def get_sandbox_info(self) -> Dict[str, Any]:
        """Get information about the sandbox without logging."""
        return self.tools.get_sandbox_info()

    def validate_target_dir(self, target_dir: str) -> Dict[str, Any]:
        """Validate a target directory without logging."""
        return self.tools.validate_target_dir(target_dir)

    def list_backups(self) -> Dict[str, Any]:
        """List available backups without logging."""
        return self.tools.list_backups()

    # ==================== DIRECT ACCESS ====================

    @property
    def raw_tools(self) -> RefactoringTools:
        """
        Provides direct access to the underlying RefactoringTools instance.

        Use this when you need to bypass the logging wrapper (not recommended
        for agent usage, but useful for testing or manual operations).
        """
        return self.tools


# ==================== CONVENIENCE FUNCTIONS ====================

def create_tool_wrapper(sandbox_path: str = "./sandbox",
                        enable_logging: bool = True) -> ToolWrapper:
    """
    Factory function to create a ToolWrapper instance.

    Args:
        sandbox_path: Path to the sandbox directory
        enable_logging: Whether to enable automatic logging

    Returns:
        Configured ToolWrapper instance
    """
    return ToolWrapper(base_sandbox=sandbox_path, enable_logging=enable_logging)


def quick_audit(file_path: str, sandbox: str = "./sandbox") -> Dict[str, Any]:
    """
    Quick utility to audit a single file without setting up full wrapper.

    Args:
        file_path: Path to the file to audit
        sandbox: Sandbox directory path

    Returns:
        Combined results from pylint analysis
    """
    tools = RefactoringTools(sandbox)
    return tools.run_pylint(file_path)


def quick_test(target: Optional[str] = None, sandbox: str = "./sandbox") -> Dict[str, Any]:
    """
    Quick utility to run tests without setting up full wrapper.

    Args:
        target: Specific file or directory to test
        sandbox: Sandbox directory path

    Returns:
        Test results from pytest
    """
    tools = RefactoringTools(sandbox)
    return tools.run_pytest(target)

