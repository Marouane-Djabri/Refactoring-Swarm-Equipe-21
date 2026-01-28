"""
Judge Agent - Exécute les tests et valide le code corrigé
"""

import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

from src.tools.test_tools import run_pytest
from src.utils.logger import log_experiment, ActionType


class JudgeAgent:
    """
    Agent responsable de la validation du code par tests
    """
    
    def __init__(self, model_name=None):
        """
        Initialise l'agent Judge
        """
        self.model_name = model_name
        print(f"Judge Agent initialisé")

    def _load_prompt(self) -> str:
        """
        Charge le prompt Judge depuis le fichier .txt
        """
        prompt_path = (
            Path(__file__).resolve()
            .parent.parent / "prompts" / "judge_prompt.txt"
        )

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"judge_prompt.txt not found in: {prompt_path}"
            )

        return prompt_path.read_text(encoding="utf-8")

    def run_tests(self, target_dir: Path) -> Dict:
        """
        Exécute les tests unitaires avec pytest
        """
        print(f"\nJudge: Running tests...")
        
        pytest_result = run_pytest(target_dir)

        success = pytest_result.get("success", False)
        output = pytest_result.get("output", "")

        print("\n" + "="*40)
        print("          PYTEST OUTPUT START \n")
        print("="*40)
        print(pytest_result)
        print("\n")
        print("="*40)
        print("           PYTEST OUTPUT END")
        print("="*40 + "\n")

        if success:
            result = {
                "status": "success",
                "message": "All tests passed. Mission complete."
            }
        else:
            failing_tests = self._extract_failures(output)
            result = {
                "status": "failure",
                "failing_tests": failing_tests
            }
        
        # Logger l'exécution des tests
        log_experiment(
            agent_name="Judge_Agent",
            model_used="pytest",
            action=ActionType.ANALYSIS if success else ActionType.DEBUG,
            details={
                "input_prompt": f"run_pytest on {target_dir}",
                "output_response": output
            },
            status="SUCCESS" if success else "FAILED"
        )
        
        return result
    
    @staticmethod
    def _extract_failures(pytest_output: str) -> List[Dict]:
        """
        Extract minimal failure information from pytest output.
        """
        failures = []

        lines = pytest_output.splitlines()
        for line in lines:
            if "FAILED" in line and "::" in line:
                parts = line.split("::")
                failures.append(
                    {
                        "file": parts[0],
                        "test": parts[1] if len(parts) > 1 else "unknown",
                        "error": line.strip()
                    }
                )

        if not failures and pytest_output:
            failures.append(
                {
                    "file": "unknown",
                    "test": "unknown",
                    "error": "Unable to clearly identify failing test."
                }
            )

        return failures
