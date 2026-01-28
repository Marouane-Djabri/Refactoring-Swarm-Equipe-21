"""
Test and Demo Script for Refactoring Tools

This script demonstrates all the capabilities of the Refactoring Tools
and can be used to verify that everything is working correctly.
"""

from src.tools.tool_wrapper import ToolWrapper
from src.tools.refactoring_tools import RefactoringTools
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ==================== PYTEST WRAPPER FOR JUDGE AGENT ====================

def run_pytest(target_dir=None):
    """
    Run pytest on a directory or file.

    This function is used by the Judge agent to execute tests.

    Args:
        target_dir: Directory or file to test (relative to sandbox)
                   If None, tests entire sandbox

    Returns:
        Dictionary containing:
            - success: Whether all tests passed
            - passed: Number of passed tests
            - failed: Number of failed tests
            - errors: Number of test errors
            - output: Full pytest output
            - summary: Human-readable summary
    """
    # Use the provided target_dir (from CLI) as the sandbox base
    sandbox_path = target_dir if target_dir else "../../sandbox"
    
    # Initialize tools with the dynamic target directory
    tools = RefactoringTools(base_sandbox=sandbox_path)
    
    # Run pytest on the root of this sandbox (None targets the base_sandbox)
    result = tools.run_pytest(None, verbose=True)

    # Return in a format the Judge agent expects
    return {
        "success": result.get("success", False),
        "passed": result.get("passed", 0),
        "failed": result.get("failed", 0),
        "errors": result.get("errors", 0),
        "total": result.get("total", 0),
        "output": result.get("full_output", ""),
        "summary": result.get("summary", ""),
        "test_path": result.get("test_path", "")
    }


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def test_security():
    """Test that security boundaries are enforced."""
    print_section("🔒 SECURITY TESTS")

    tools = RefactoringTools(base_sandbox="./sandbox")

    # Test 1: Try to write outside sandbox
    print("Test 1: Attempting to write outside sandbox...")
    try:
        result = tools.write_file("../src/agents/malicious.py", "bad code")
        print(f"❌ SECURITY FAILURE: Write was allowed! {result}")
    except PermissionError as e:
        print(f"✅ SECURITY OK: Access denied as expected")
        print(f"   Message: {str(e)[:80]}...")

    # Test 2: Try to read outside sandbox
    print("\nTest 2: Attempting to read outside sandbox...")
    try:
        result = tools.read_file("../../requirements.txt")
        if result["success"]:
            print(f"❌ SECURITY FAILURE: Read was allowed!")
        else:
            print(f"✅ SECURITY OK: Access denied")
            print(f"   Error: {result['error'][:80]}...")
    except PermissionError as e:
        print(f"✅ SECURITY OK: Access denied as expected")

    print("\n🎉 Security tests passed!")


def test_auditor_tools():
    """Test the Auditor's tools."""
    print_section("🔍 AUDITOR TOOLS TEST")

    tools = RefactoringTools(base_sandbox="./sandbox")

    # Create a test file with intentional issues
    test_code = """
# Bad code for testing pylint
def badFunction(x,y):
    z=x+y
    return z

def unused_function():
    pass

x = badFunction(1,2)
"""

    print("Creating test file: test_code.py")
    write_result = tools.write_file("test_code.py", test_code)

    if not write_result["success"]:
        print(f"❌ Failed to create test file: {write_result['error']}")
        return

    print(f"✅ Created test file: {write_result['path']}")

    # Test read_file
    print("\n--- Testing read_file() ---")
    read_result = tools.read_file("test_code.py")

    if read_result["success"]:
        print(f"✅ Read successful")
        print(f"   Lines: {read_result['lines']}")
        print(f"   Size: {read_result['size_bytes']} bytes")
    else:
        print(f"❌ Read failed: {read_result['error']}")

    # Test list_files
    print("\n--- Testing list_files() ---")
    list_result = tools.list_files("*.py")

    if list_result["success"]:
        print(f"✅ Found {list_result['count']} Python files:")
        for file in list_result["files"]:
            print(f"   - {file}")
    else:
        print(f"❌ List failed: {list_result['error']}")

    # Test run_pylint
    print("\n--- Testing run_pylint() ---")
    pylint_result = tools.run_pylint("test_code.py")

    if pylint_result["success"]:
        print(f"✅ Pylint analysis complete")
        print(f"   Score: {pylint_result['score']}/10")
        print(f"   Total Issues: {pylint_result['total_issues']}")
        print(f"   - Errors: {len(pylint_result['errors'])}")
        print(f"   - Warnings: {len(pylint_result['warnings'])}")
        print(f"   - Conventions: {len(pylint_result['conventions'])}")
        print(f"\n   Summary: {pylint_result['summary']}")

        if pylint_result['conventions']:
            print(f"\n   Example issue: {pylint_result['conventions'][0]}")
    else:
        print(f"❌ Pylint failed: {pylint_result['error']}")


def test_fixer_tools():
    """Test the Fixer's tools."""
    print_section("✏️ FIXER TOOLS TEST")

    tools = RefactoringTools(base_sandbox="./sandbox")

    # Create original file
    original_code = """
def calculate(a, b):
    return a + b
"""

    print("Creating original file: fixer_test.py")
    tools.write_file("fixer_test.py", original_code, create_backup=False)

    # Test backup creation
    print("\n--- Testing create_backup() ---")
    backup_result = tools.create_backup("fixer_test.py")

    if backup_result["success"]:
        print(f"✅ Backup created")
        print(f"   Original: {backup_result['original_path']}")
        print(f"   Backup: {Path(backup_result['backup_path']).name}")
    else:
        print(f"❌ Backup failed: {backup_result['error']}")

    # Test write_file with automatic backup
    print("\n--- Testing write_file() with auto-backup ---")
    refactored_code = """
def calculate(first_number: int, second_number: int) -> int:
    \"\"\"
    Calculate the sum of two numbers.
    
    Args:
        first_number: The first number
        second_number: The second number
        
    Returns:
        The sum of the two numbers
    \"\"\"
    return first_number + second_number
"""

    write_result = tools.write_file(
        "fixer_test.py", refactored_code, create_backup=True)

    if write_result["success"]:
        print(f"✅ File written with backup")
        print(f"   Lines: {write_result['lines_written']}")
        print(
            f"   Backup: {Path(write_result['backup_path']).name if write_result['backup_path'] else 'None'}")
    else:
        print(f"❌ Write failed: {write_result['error']}")

    # Test list_backups
    print("\n--- Testing list_backups() ---")
    backups_result = tools.list_backups()

    if backups_result["success"]:
        print(f"✅ Found {backups_result['count']} backups:")
        for backup in backups_result["backups"][:3]:  # Show first 3
            print(f"   - {backup['name']} ({backup['size_bytes']} bytes)")
    else:
        print(f"❌ List backups failed: {backups_result['error']}")

    # Test restore_backup
    if backups_result["success"] and backups_result["count"] > 0:
        print("\n--- Testing restore_backup() ---")
        latest_backup = backups_result["backups"][0]["path"]

        restore_result = tools.restore_backup(
            latest_backup, "fixer_test_restored.py")

        if restore_result["success"]:
            print(f"✅ Backup restored")
            print(f"   From: {Path(restore_result['from_backup']).name}")
            print(f"   To: fixer_test_restored.py")
        else:
            print(f"❌ Restore failed: {restore_result['error']}")


def test_judge_tools():
    """Test the Judge's tools."""
    print_section("⚖️ JUDGE TOOLS TEST")

    tools = RefactoringTools(base_sandbox="./sandbox")

    # Create a simple module with a function
    module_code = """
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b

def subtract(a: int, b: int) -> int:
    \"\"\"Subtract b from a.\"\"\"
    return a - b
"""

    # Create a test file
    test_code = """
from calculator import add, subtract

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0

def test_subtract():
    assert subtract(5, 3) == 2
    assert subtract(0, 0) == 0
    assert subtract(-1, -1) == 0
"""

    print("Creating test files...")
    tools.write_file("calculator.py", module_code, create_backup=False)
    tools.write_file("test_calculator.py", test_code, create_backup=False)
    print("✅ Test files created")

    # Test run_pytest
    print("\n--- Testing run_pytest() ---")
    pytest_result = tools.run_pytest("test_calculator.py", verbose=True)

    if pytest_result["success"]:
        print(f"✅ Tests passed!")
        print(f"   Passed: {pytest_result['passed']}")
        print(f"   Failed: {pytest_result['failed']}")
        print(f"   Total: {pytest_result['total']}")
        print(f"\n   {pytest_result['summary']}")
    else:
        print(f"⚠️ Tests failed or had errors")
        print(f"   Passed: {pytest_result.get('passed', 0)}")
        print(f"   Failed: {pytest_result.get('failed', 0)}")
        print(f"   Error: {pytest_result.get('error', 'Unknown')}")

        if 'summary' in pytest_result:
            print(f"\n   {pytest_result['summary']}")

    # Create a test with intentional failure
    print("\n--- Testing with failing tests ---")
    failing_test = """
from calculator import add

def test_intentional_failure():
    assert add(2, 2) == 5  # This should fail
"""

    tools.write_file("test_failing.py", failing_test, create_backup=False)

    fail_result = tools.run_pytest("test_failing.py", verbose=True)

    print(f"\nExpected failure result:")
    print(f"   Success: {fail_result['success']} (should be False)")
    print(f"   Failed: {fail_result.get('failed', 0)} (should be > 0)")

    # Check if we can distinguish error types
    if "AssertionError" in fail_result.get("full_output", ""):
        print(f"   ✅ Can detect assertion failures")

    # Create a test with syntax error
    print("\n--- Testing with syntax error ---")
    syntax_error_code = """
def broken_function(
    return "missing closing parenthesis"
"""

    tools.write_file("broken.py", syntax_error_code, create_backup=False)

    syntax_result = tools.run_pytest("broken.py", verbose=False)

    print(f"\nSyntax error result:")
    print(f"   Success: {syntax_result['success']} (should be False)")

    if "SyntaxError" in syntax_result.get("full_output", ""):
        print(f"   ✅ Can detect syntax errors")


def test_tool_wrapper():
    """Test the ToolWrapper with logging."""
    print_section("📊 TOOL WRAPPER TEST (with logging)")

    # Create wrapper with logging disabled for testing
    wrapper = ToolWrapper(base_sandbox="./sandbox", enable_logging=False)

    print("Creating test file using wrapper...")

    test_code = """
def greet(name: str) -> str:
    \"\"\"Greet someone by name.\"\"\"
    return f"Hello, {name}!"
"""

    # Test audit methods
    write_result = wrapper.fixer_write_file(
        "wrapper_test.py",
        test_code,
        agent_name="TestFixer",
        model_used="test-model"
    )

    if write_result["success"]:
        print(f"✅ File written via wrapper")

    # Test audit
    audit_result = wrapper.audit_run_pylint(
        "wrapper_test.py",
        agent_name="TestAuditor",
        model_used="test-model"
    )

    if audit_result["success"]:
        print(f"✅ Audit completed via wrapper")
        print(f"   Score: {audit_result['score']}/10")

    print("\n💡 Note: Logging was disabled for this test")
    print("   In production, set enable_logging=True to log all interactions")


def test_sandbox_info():
    """Test utility methods."""
    print_section("ℹ️ SANDBOX INFO")

    tools = RefactoringTools(base_sandbox="./sandbox")

    info = tools.get_sandbox_info()

    print("Sandbox Information:")
    print(f"  Path: {info['sandbox_path']}")
    print(f"  Exists: {info['exists']}")
    print(f"  Python Files: {info['total_python_files']}")
    print(f"  Test Files: {info['test_files']}")
    print(f"  Backups: {info['backups_available']}")


def main():
    """Run all tests."""
    print("\n" + "🚀" * 30)
    print(" REFACTORING TOOLS - TEST SUITE")
    print("🚀" * 30)

    # Ensure sandbox exists
    sandbox_path = Path("./sandbox")
    sandbox_path.mkdir(exist_ok=True)

    try:
        # Run all tests
        test_security()
        test_auditor_tools()
        test_fixer_tools()
        test_judge_tools()
        test_tool_wrapper()
        test_sandbox_info()

        # Final summary
        print_section("✅ ALL TESTS COMPLETED")
        print("The Refactoring Tools are ready for integration!")
        print("\nNext steps:")
        print("  1. Integrate tools into your Orchestrator")
        print("  2. Update agent prompts to use structured output")
        print("  3. Test with real refactoring scenarios")
        print("  4. Review logs/experiment_data.json for telemetry")

    except Exception as e:
        print(f"\n❌ Test suite failed with error:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
