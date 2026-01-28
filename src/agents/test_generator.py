"""
TestGenerator Agent - Generates Pytest unit tests for corrected Python files
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from mistralai import Mistral
from src.utils.logger import log_experiment, ActionType

class TestGeneratorAgent:
    """
    Agent responsible for generating unit tests for cleaned/corrected code.
    """
    def __init__(self, model_name: str = "mistral-large-latest"):
        self.model_name = model_name
        
        load_dotenv()
        api_key = os.getenv("MISTRAL_API_KEY")
        
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not found in .env!")
            
        self.client = Mistral(api_key=api_key)
        print(f"TestGenerator Agent initialized with model: {model_name}")

    def _load_prompt(self) -> str:
        """
        Loads the prompt from the prompts directory
        """
        prompt_path = Path(__file__).parent.parent / "prompts" / "test_generator_prompt.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found at {prompt_path}")
            
        return prompt_path.read_text(encoding="utf-8")

    def _clean_code(self, code: str) -> str:
        """
        Cleans generated code to remove markdown blocks if present
        """
        if code.strip().startswith("```python"):
            code = code.strip()[len("```python"):].strip()
        elif code.strip().startswith("```"):
            code = code.strip()[3:].strip()
        
        if code.strip().endswith("```"):
            code = code.strip()[:-3].strip()
        
        return code

    def generate_unit_tests(self, target_dir: str):
        """
        Scans the directory for python files (excluding test_*.py) and generates tests for them.
        """
        print("\nTestGenerator: Generating unit tests...")
        target_path = Path(target_dir)
        
        if not target_path.exists():
            print(f"Target directory {target_dir} does not exist.")
            return

        # Find python files that are not tests
        py_files = [f for f in target_path.glob("*.py") if not f.name.startswith("test_")]
        
        if not py_files:
            print("No source Python files found to test.")
            return

        base_prompt = self._load_prompt()
        
        for py_file in py_files:
            test_filename = f"test_{py_file.name}"
            test_file_path = target_path / test_filename
            
            # Skip if test file already exists? Maybe redundant if we want to regenerate?
            # Let's regenerate to ensure they match the FIXED code.
            
            code_content = py_file.read_text(encoding="utf-8")
            
            # Format prompt
            prompt = base_prompt.replace("{filename}", py_file.name).replace("{code}", code_content)
            
            try:
                print(f"Generating tests for {py_file.name}...")
                response = self.client.chat.complete(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                generated_code = self._clean_code(response.choices[0].message.content)
                
                test_file_path.write_text(generated_code, encoding="utf-8")
                print(f"Created {test_filename}")
                
                log_experiment(
                    agent_name="TestGenerator_Agent",
                    model_used=self.model_name,
                    action=ActionType.GENERATION,
                    details={
                        "source_file": py_file.name,
                        "generated_test_file": test_filename,
                        "status": "SUCCESS",
                        "input_prompt": prompt,
                        "output_response": generated_code,
                        "raw_llm_response": response.choices[0].message.content,
                        "generated_code_length": len(generated_code)
                    },
                    status="SUCCESS"
                )
                
            except Exception as e:
                print(f"Error generating tests for {py_file.name}: {e}")
                log_experiment(
                    agent_name="TestGenerator_Agent",
                    model_used=self.model_name,
                    action=ActionType.GENERATION,
                    details={
                        "source_file": py_file.name,
                        "error": str(e)
                    },
                    status="FAILED"
                )
