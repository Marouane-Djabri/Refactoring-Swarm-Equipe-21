# Refactoring Tools - The Internal API

## Overview

The `src/tools/` module provides the **"Hands and Eyes"** of The Refactoring Swarm. It contains the Internal API that allows agents (Auditor, Fixer, Judge) to safely interact with code files while maintaining strict security boundaries.

## Architecture

```
src/tools/
├── refactoring_tools.py    # Core tools implementation
├── tool_wrapper.py          # High-level wrapper with logging
├── __init__.py              # Module exports
└── README.md                # This file
```

## Core Components

### 1. RefactoringTools Class

The main class that provides all file operations, static analysis, and testing capabilities.

**Key Features:**
- ✅ **Security First**: All file operations are restricted to the sandbox
- ✅ **Comprehensive Error Handling**: All methods return structured dictionaries with success/failure status
- ✅ **Automatic Backups**: File modifications can automatically create timestamped backups
- ✅ **Detailed Results**: All tools return structured data perfect for LLM consumption

### 2. ToolWrapper Class

A high-level wrapper that adds automatic logging and telemetry to every tool call.

**Benefits:**
- Automatically logs all agent interactions for scientific analysis
- Integrates seamlessly with `src/utils/logger.py`
- Provides specialized methods for each agent role
- Tracks ActionType (ANALYSIS, FIX, DEBUG) appropriately

## Security Model

### The Sandbox Guard

Every file operation passes through the `_safe_path()` method, which:

1. Resolves the absolute path
2. Checks if it's within the sandbox boundary
3. Raises `PermissionError` if access is denied

**Example:**
```python
tools = RefactoringTools(base_sandbox="./sandbox")

# ✅ ALLOWED: Writing to sandbox/my_code.py
tools.write_file("my_code.py", "print('hello')")

# ❌ BLOCKED: Attempting to write to ../src/agents/auditor.py
tools.write_file("../src/agents/auditor.py", "malicious code")
# Raises: PermissionError: SECURITY VIOLATION
```

## Tool Categories

### 🔍 Auditor Tools (Read-Only)

The Auditor's "eyes" - allows reading and analyzing code without modification.

#### `read_file(file_name: str) -> Dict`

Reads a file from the sandbox.

**Returns:**
```python
{
    "success": True,
    "content": "file content...",
    "path": "/absolute/path/to/file.py",
    "size_bytes": 1234,
    "lines": 45,
    "error": None
}
```

**Usage:**
```python
tools = RefactoringTools()
result = tools.read_file("my_script.py")

if result["success"]:
    code = result["content"]
    print(f"Read {result['lines']} lines")
```

#### `list_files(pattern: str = "*.py") -> Dict`

Lists all files in the sandbox matching a pattern.

**Returns:**
```python
{
    "success": True,
    "files": ["main.py", "utils.py", "tests/test_main.py"],
    "count": 3,
    "pattern": "*.py"
}
```

#### `run_pylint(file_name: str) -> Dict`

Runs pylint static analysis on a file.

**Returns:**
```python
{
    "success": True,
    "score": 7.5,
    "raw_output": "Your code has been rated at 7.50/10...",
    "errors": [{"line": 10, "message": "undefined variable"}],
    "warnings": [...],
    "conventions": [...],
    "refactors": [...],
    "total_issues": 15,
    "summary": "Score: 7.5/10\nErrors: 2, Warnings: 5..."
}
```

**Usage for Auditor Agent:**
```python
# Get the initial quality score
result = tools.run_pylint("buggy_code.py")

if result["success"]:
    score = result["score"]
    issues = result["total_issues"]
    
    # Send to LLM: "This file scores {score}/10 with {issues} issues"
    prompt = f"""
    File Analysis:
    - Pylint Score: {score}/10
    - Total Issues: {issues}
    - Errors: {len(result['errors'])}
    
    Issues Found:
    {result['raw_output']}
    
    Please analyze these issues and suggest refactoring priorities.
    """
```

### ✏️ Fixer Tools (Write Operations)

The Fixer's "hands" - allows modifying code safely.

#### `write_file(file_name: str, content: str, create_backup: bool = True) -> Dict`

Writes content to a file in the sandbox.

**Returns:**
```python
{
    "success": True,
    "path": "/absolute/path/to/file.py",
    "backup_path": "/absolute/path/to/.backups/file_20260111_143022.py",
    "bytes_written": 1500,
    "lines_written": 50,
    "error": None
}
```

**Usage for Fixer Agent:**
```python
# Receive refactored code from LLM
refactored_code = llm_response["code"]

# Write it to the file (backup created automatically)
result = tools.write_file("my_script.py", refactored_code)

if result["success"]:
    print(f"✅ Wrote {result['lines_written']} lines")
    print(f"📦 Backup saved to: {result['backup_path']}")
else:
    print(f"❌ Error: {result['error']}")
```

#### `create_backup(file_name: str) -> Dict`

Manually creates a timestamped backup of a file.

**Returns:**
```python
{
    "success": True,
    "backup_path": "/path/to/.backups/file_20260111_143022.py",
    "original_path": "/path/to/file.py",
    "timestamp": "20260111_143022"
}
```

#### `restore_backup(backup_path: str, target_file: str) -> Dict`

Restores a file from a backup (useful if refactoring breaks everything).

**Returns:**
```python
{
    "success": True,
    "restored_to": "/path/to/file.py",
    "from_backup": "/path/to/.backups/file_20260111_143022.py"
}
```

**Usage for Self-Healing:**
```python
# If Judge reports test failures, restore the backup
if judge_result["failed"] > 0:
    backups = tools.list_backups()
    latest_backup = backups["backups"][0]["path"]
    
    tools.restore_backup(latest_backup, "my_script.py")
    print("⏮️ Restored previous working version")
```

#### `list_backups() -> Dict`

Lists all available backups with timestamps.

**Returns:**
```python
{
    "success": True,
    "backups": [
        {
            "name": "my_script_20260111_143022.py",
            "path": "/path/to/.backups/my_script_20260111_143022.py",
            "size_bytes": 1500,
            "modified": "2026-01-11T14:30:22"
        }
    ],
    "count": 1
}
```

### ⚖️ Judge Tools (Validation)

The Judge's tools for verifying that refactored code still works.

#### `run_pytest(target: Optional[str] = None, verbose: bool = True) -> Dict`

Runs pytest on the sandbox or a specific file/directory.

**Returns:**
```python
{
    "success": True,  # True if all tests passed
    "passed": 10,
    "failed": 0,
    "errors": 0,
    "skipped": 1,
    "total": 11,
    "stdout": "test_main.py::test_function PASSED...",
    "stderr": "",
    "full_output": "Combined stdout + stderr",
    "return_code": 0,
    "test_path": "/path/to/sandbox",
    "summary": "Total: 11 tests | ✅ Passed: 10 | ⏭️ Skipped: 1\n✅ ALL TESTS PASSED!"
}
```

**Usage for Judge Agent:**
```python
# After Fixer applies changes, validate them
result = tools.run_pytest("my_script.py")

if result["success"]:
    print(f"✅ All {result['passed']} tests passed!")
    # Tell Orchestrator: refactoring successful
else:
    # Extract failure details to send back to Fixer
    failures = result["full_output"]
    
    prompt = f"""
    Your refactoring caused test failures:
    
    Passed: {result['passed']}
    Failed: {result['failed']}
    
    Error Output:
    {failures}
    
    Please fix these issues while preserving the refactoring improvements.
    """
```

**Distinguishing Error Types:**

The tool helps distinguish between different failure modes:

- **Syntax Error**: `success=False` + low/zero test count + syntax errors in output
- **Failed Assertion**: `success=False` + tests run but `failed > 0`
- **Import Error**: Look for "ImportError" or "ModuleNotFoundError" in `full_output`
- **All Pass**: `success=True` + `failed == 0`

**Example Error Analysis:**
```python
result = tools.run_pytest()

if not result["success"]:
    if "SyntaxError" in result["full_output"]:
        error_type = "SYNTAX_ERROR"
        message = "The refactored code has syntax errors"
    elif result["failed"] > 0:
        error_type = "ASSERTION_FAILURE"
        message = f"{result['failed']} test assertions failed"
    elif "ImportError" in result["full_output"]:
        error_type = "IMPORT_ERROR"
        message = "Missing imports or dependencies"
    
    # Send specific error type back to Fixer
    feedback = {
        "error_type": error_type,
        "message": message,
        "details": result["full_output"]
    }
```

## Using the ToolWrapper

For agent implementations, use the `ToolWrapper` class which adds automatic logging:

```python
from src.tools import ToolWrapper

# Initialize with logging enabled
wrapper = ToolWrapper(base_sandbox="./sandbox", enable_logging=True)

# Auditor usage
result = wrapper.audit_run_pylint(
    file_name="my_code.py",
    agent_name="Auditor",
    model_used="gemini-1.5-flash"
)
# Automatically logs to experiment_data.json

# Fixer usage
result = wrapper.fixer_write_file(
    file_name="my_code.py",
    content=refactored_code,
    agent_name="Fixer",
    model_used="gemini-1.5-flash"
)
# Automatically logs the fix action

# Judge usage
result = wrapper.judge_run_pytest(
    target="my_code.py",
    agent_name="Judge",
    model_used="gemini-1.5-flash"
)
# Automatically logs the validation
```

## Integration with main.py

The tools support the `--target_dir` argument from `main.py`:

```python
import sys
from src.tools import RefactoringTools

# Get target directory from command line
if len(sys.argv) > 1 and sys.argv[1] == "--target_dir":
    target_dir = sys.argv[2]
else:
    target_dir = "./sandbox"

# Validate it's safe
tools = RefactoringTools(base_sandbox=target_dir)
validation = tools.validate_target_dir(target_dir)

if validation["valid"]:
    print(f"✅ Using target directory: {validation['path']}")
    # Proceed with refactoring
else:
    print(f"❌ Invalid target: {validation['error']}")
    sys.exit(1)
```

## Error Handling Best Practices

All tools return structured dictionaries, never raise exceptions (except for security violations). Always check the `success` field:

```python
# ✅ CORRECT: Check success before using results
result = tools.read_file("nonexistent.py")

if result["success"]:
    content = result["content"]
    # Process content
else:
    error_message = result["error"]
    # Handle error gracefully
    print(f"Could not read file: {error_message}")
    
    # Maybe inform the LLM
    prompt = f"Error: {error_message}. Please try a different file."

# ❌ INCORRECT: Assuming success
result = tools.read_file("nonexistent.py")
content = result["content"]  # This will be None! Program might crash
```

## Telemetry and Logging

Every tool call through `ToolWrapper` is automatically logged with:

- **Agent Name**: Which agent made the call
- **Model Used**: Which LLM model was used
- **Action Type**: ANALYSIS, FIX, DEBUG, or GENERATION
- **Input Data**: What was requested
- **Output Data**: What was returned
- **Status**: SUCCESS or FAILURE

This data feeds into `logs/experiment_data.json` for scientific analysis.

**Disable Logging (for testing):**
```python
wrapper = ToolWrapper(enable_logging=False)
```

## Quick Start Example

Complete example of an audit-fix-judge cycle:

```python
from src.tools import ToolWrapper

# Initialize
tools = ToolWrapper(base_sandbox="./sandbox")

# 1. AUDITOR: Find problems
print("🔍 Step 1: Audit")
audit_result = tools.audit_run_pylint(
    "buggy_code.py",
    agent_name="Auditor",
    model_used="gemini-1.5-flash"
)

print(f"Initial score: {audit_result['score']}/10")
print(f"Issues found: {audit_result['total_issues']}")

# 2. FIXER: Apply fixes (would come from LLM)
print("\n✏️ Step 2: Fix")
refactored_code = """
def hello(name):
    '''Greet a person by name.'''
    return f"Hello, {name}!"
"""

fix_result = tools.fixer_write_file(
    "buggy_code.py",
    refactored_code,
    agent_name="Fixer",
    model_used="gemini-1.5-flash"
)

if fix_result["success"]:
    print(f"✅ Applied fixes ({fix_result['lines_written']} lines)")

# 3. JUDGE: Validate
print("\n⚖️ Step 3: Validate")
test_result = tools.judge_run_pytest(
    agent_name="Judge",
    model_used="gemini-1.5-flash"
)

if test_result["success"]:
    print(f"✅ All {test_result['passed']} tests passed!")
    
    # 4. Re-audit to measure improvement
    print("\n📊 Step 4: Measure Improvement")
    final_audit = tools.audit_run_pylint(
        "buggy_code.py",
        agent_name="Auditor",
        model_used="gemini-1.5-flash"
    )
    
    improvement = final_audit["score"] - audit_result["score"]
    print(f"Score improved by: +{improvement:.2f} points")
else:
    print(f"❌ {test_result['failed']} tests failed")
    print("Restoring backup...")
    
    # Restore the backup
    backups = tools.list_backups()
    if backups["count"] > 0:
        latest = backups["backups"][0]["path"]
        tools.fixer_restore_backup(
            latest, 
            "buggy_code.py",
            agent_name="Fixer",
            model_used="gemini-1.5-flash"
        )
```

## Checklist for Integration

Before considering the Toolsmith role complete, verify:

- ✅ Does my tool prevent writing to `/src` or root? → **Yes, via `_safe_path()`**
- ✅ Does `run_pylint` return a score that the Auditor can use to measure improvement? → **Yes, returns numeric score 0-10**
- ✅ Can my `run_pytest` tool distinguish between "Syntax Error" and "Failed Assertion"? → **Yes, via output parsing and return code analysis**
- ✅ Does every tool handle the `--target_dir` argument passed from `main.py`? → **Yes, via `base_sandbox` parameter**
- ✅ Is every tool interaction ready to be logged via `log_experiment`? → **Yes, via ToolWrapper**
- ✅ Do tools return helpful error messages instead of crashing? → **Yes, all return structured dicts with error fields**

## Testing the Tools

Run the test/demo script to verify everything works:

```bash
python src/tools/test_tools.py
```

This will:
1. Create a test file in the sandbox
2. Run pylint on it
3. Apply a "fix"
4. Run tests
5. Show all results

## Next Steps

1. **Orchestrator Integration**: The Orchestrator should import and use these tools
2. **Agent Prompts**: Update agent prompts to use the structured output format
3. **Error Recovery**: Implement the self-healing loop using pytest feedback
4. **Telemetry Review**: Check `logs/experiment_data.json` after runs to ensure proper logging

## API Reference

See the docstrings in `refactoring_tools.py` for complete parameter and return value documentation.
