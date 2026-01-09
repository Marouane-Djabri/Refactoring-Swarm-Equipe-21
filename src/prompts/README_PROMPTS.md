This file summarizes the system prompts for the three agents and what the Toolsmith / Orchestrator must provide.

## Files

- `src/prompts/auditor_prompt.txt`
- `src/prompts/fixer_prompt.txt`
- `src/prompts/judge_prompt.txt`

## Expected tools

All prompts assume these callable tools :

- `list_files(target_dir: str)` → list files/directories in the sandbox.
- `read_file(path: str)` → read a text file from the sandbox.
- `write_file(path: str, content: str)` → overwrite a text file in the sandbox.
- `run_pylint(target_dir: str)` → run pylint on the project and return the report text.
- `run_pytest(target_dir: str)` → run pytest on the project and return full test output.

The Toolsmith should implement and expose functions with these behaviours to the agents.

## Auditor – expected output

Output JSON:

```json
{
  "summary": "Overall assessment of the codebase.",
  "issues": [
    {
      "file": "path/to/file.py",
      "location": "function name, class name, or line number if known",
      "severity": "error|warning|style",
      "problem": "Short description of the issue.",
      "suggested_fix": "Concrete instructions on how to fix the issue."
    }
  ]
}
```
## Fixer – expected output

```json
{
  "applied_changes": [
    {
      "file": "path/to/file.py",
      "description": "What was changed and why."
    }
  ],
  "notes": "Any important comments, assumptions, or limitations."
}
```

## Judge – expected output

if all tests pass:

```json
{
  "status": "success",
  "message": "All tests passed. Mission complete."
}
```

if some tests fail:

```json
{
  "status": "failure",
  "failing_tests": [
    {
      "file": "path/to/test_file.py",
      "test": "test_name_if_known",
      "error": "Short description or main traceback message."
    }
  ]
}
```