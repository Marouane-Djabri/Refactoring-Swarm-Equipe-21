import io
import sys
from unittest.mock import patch

def test_conditional_print():
    # Capture stdout
    captured_output = io.StringIO()
    with patch('sys.stdout', new=captured_output):
        # Import the module to trigger the conditional print
        import syntax_error
    # Check if "OK" was printed
    assert captured_output.getvalue().strip() == "OK"