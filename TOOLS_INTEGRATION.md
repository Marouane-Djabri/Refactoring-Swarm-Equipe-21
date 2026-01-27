# Tools Integration Summary

## Overview

The RefactoringTools have been successfully integrated into the orchestrator. The orchestrator now:

1. ✅ Initializes RefactoringTools at startup
2. ✅ Passes tools through the LangGraph workflow state
3. ✅ Validates the sandbox before execution
4. ✅ Logs tool usage and sandbox information
5. ✅ Provides tool status in the final report

## Integration Points

### 1. Orchestrator Initialization

The `LangGraphOrchestrator` now accepts a `target_dir` parameter:

```python
orchestrator = LangGraphOrchestrator(
    max_iterations=10,
    model_name="gemini-2.5-flash",
    target_dir="./sandbox"  # NEW: sandbox directory
)
```

The orchestrator initializes RefactoringTools and displays sandbox status:

```
🔧 Initializing RefactoringTools...
   ✅ Sandbox: E:\path\to\sandbox
   ✅ Python files in sandbox: 5
   ✅ Test files: 3
   ✅ Backups available: 0
```

### 2. State Schema Update

The `RefactoringState` now includes a `tools` field:

```python
class RefactoringState(TypedDict):
    target_dir: str
    python_files: List[Path]
    tools: RefactoringTools  # NEW: shared tools instance
    # ... other fields
```

This allows all agents to access the same tools through the state:

```python
def _auditor_node(self, state: RefactoringState) -> RefactoringState:
    tools = state["tools"]  # Access tools
    # Use tools for analysis
    return state
```

### 3. Workflow State Initialization

The initial state now includes the tools instance:

```python
initial_state: RefactoringState = {
    "target_dir": str(target_path),
    "python_files": python_files,
    "tools": self.tools,  # NEW: pass tools to agents
    # ... other fields
}
```

### 4. Sandbox Validation

New method to validate the sandbox:

```python
def validate_sandbox(self, target_dir: str) -> bool:
    """Valide que le répertoire cible est accessible"""
    validation = self.tools.validate_target_dir(target_dir)
    if not validation.get("valid"):
        print(f"❌ Erreur: {validation.get('error')}")
        return False
    return True
```

### 5. Enhanced Logging

Tool usage is now logged in the experiment telemetry:

```python
log_experiment(
    agent_name="LangGraph_Orchestrator",
    details={
        # ... other details
        "tools_used": {
            "sandbox_path": self.sandbox_info['sandbox_path'],
            "backups_created": self.sandbox_info['backups_available'],
            "test_files": self.sandbox_info['test_files']
        }
    }
)
```

## Available Tools to Agents

Through the state, agents can now access:

### File Operations
```python
tools = state["tools"]

# Read files
result = tools.read_file("my_code.py")
if result["success"]:
    content = result["content"]

# Write files with backups
result = tools.write_file("my_code.py", refactored_code, create_backup=True)

# Create backups
backup = tools.create_backup("my_code.py")

# List files
files = tools.list_files("*.py")

# Restore from backup
tools.restore_backup(backup["backup_path"], "my_code.py")
```

### Static Analysis
```python
# Run pylint
result = tools.run_pylint("my_code.py")
score = result["score"]  # 0-10
issues = result["total_issues"]
```

### Testing
```python
# Run pytest
result = tools.run_pytest("test_file.py")
if result["success"]:
    print(f"✅ {result['passed']} tests passed")
else:
    print(f"❌ {result['failed']} tests failed")
```

### Utilities
```python
# Get sandbox info
info = tools.get_sandbox_info()

# Validate a directory
validation = tools.validate_target_dir("./sandbox")

# List backups
backups = tools.list_backups()
```

## How Agents Use Tools

### Auditor Agent Example

```python
def analyze(self, target_dir: Path) -> Dict:
    # Access tools from somewhere (current approach via file_operations)
    files = list_files(target_dir)
    
    for file_path in files:
        content = read_file(file_path)
        pylint_report = run_pylint(file_path)
        # ... analysis logic
```

### Fixer Agent Example

```python
def fix_code(self, refactoring_plan: Dict) -> Dict:
    for issue in refactoring_plan.get("issues", []):
        file_path = issue["file"]
        
        original_code = read_file(file_path)
        backup_file(file_path)  # Create backup
        
        # Get refactored code from LLM
        fixed_code = llm.generate_content(prompt)
        
        write_file(file_path, fixed_code)  # Write with backup
```

### Judge Agent Example

```python
def run_tests(self, target_dir: Path) -> Dict:
    pytest_result = run_pytest(target_dir)
    
    if pytest_result.get("success"):
        return {"status": "success"}
    else:
        failures = pytest_result.get("full_output")
        return {"status": "failure", "failing_tests": failures}
```

## Security Features

### Sandbox Boundary Enforcement

All file operations are protected by `validate_path()`:

- ✅ Cannot read files outside sandbox
- ✅ Cannot write files outside sandbox
- ✅ Cannot access parent directories
- ✅ Automatic backup before writes

### Example

```python
# ✅ ALLOWED - within sandbox
read_file("my_code.py")

# ❌ BLOCKED - outside sandbox
read_file("../../../sensitive_file.py")  
# Raises: PermissionError: SECURITY VIOLATION
```

## Error Handling

All tool operations return structured responses:

```python
result = tools.read_file("file.py")

if result["success"]:
    # Use result
    content = result["content"]
else:
    # Handle error gracefully
    error = result["error"]
    # Inform LLM or retry
```

Never raises unexpected exceptions - errors are returned in the result dictionary.

## Telemetry

All agent-tool interactions are automatically logged to `logs/experiment_data.json`:

- Agent name
- Model used
- Action type (ANALYSIS, FIX, DEBUG)
- Input/output details
- Success/failure status

## Next Steps for Agents

To fully leverage the tools, agents should:

1. ✅ Use the tool wrapper functions from `src.tools.*` modules
2. ✅ Always check the `success` field in responses
3. ✅ Provide meaningful error feedback to other agents
4. ✅ Take advantage of backups for safe refactoring

## Example: Complete Workflow

```python
from src.orchestrator import LangGraphOrchestrator

# Create orchestrator with integrated tools
orchestrator = LangGraphOrchestrator(
    max_iterations=10,
    model_name="gemini-2.5-flash",
    target_dir="./sandbox"
)

# Run the workflow
result = orchestrator.run("./sandbox")

if result["success"]:
    print(f"✅ Refactoring successful!")
    print(f"   Iterations needed: {result['iterations_needed']}")
else:
    print(f"❌ Refactoring failed")
    print(f"   Reason: {result['reason']}")
```

The orchestrator will:

1. 🔧 Initialize RefactoringTools
2. 📊 Validate the sandbox
3. 🔍 Run Auditor with tools access
4. ✏️ Run Fixer with tools access
5. ⚖️ Run Judge with tools access
6. 📈 Log all interactions and tool usage
7. 🔄 Loop until success or max iterations
8. 📝 Generate final report with tool statistics

## Summary

The tools are now fully integrated into the orchestrator workflow:

- ✅ Tools initialized and configured
- ✅ Tools available to all agents through state
- ✅ Sandbox security enforced throughout
- ✅ Complete telemetry and logging
- ✅ Error handling and recovery mechanisms
- ✅ Backup/restore for safe refactoring

The refactoring swarm can now operate as a cohesive unit with shared, secure access to the sandbox environment.
