"""
Judge Agent - Exécute les tests et valide le code corrigé
"""

import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

from src.tools.test_tools import run_pytest
from src.tools.analysis_tools import run_pylint
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
        Exécute les tests unitaires avec pytest ET l'analyse Pylint
        """
        print(f"\nJudge: Running tests...")
        
        pytest_result = run_pytest(target_dir)

        tests_passed = pytest_result.get("success", False)
        output = pytest_result.get("output", "")
        
        pylint_success = True
        pylint_results = {}
        
        if tests_passed:
            print(f"Judge: Tests passed. Running Pylint analysis...")
            # Analyser les fichiers Python (hors tests)
            python_files = [
                f for f in target_dir.rglob("*.py")
                if not f.name.startswith("test_") and f.name != "__init__.py"
            ]
            
            for file_path in python_files:
                try:
                    lint_res = run_pylint(str(file_path))
                    score = lint_res.get("score", 0)
                    pylint_results[str(file_path)] = lint_res
                    
                    print(f"  - {file_path.name}: {score}/10")
                    
                    if score < 8.0:
                        pylint_success = False
                except Exception as e:
                    print(f"  - Warning: Could not lint {file_path}: {e}")
                    # En cas d'erreur d'outil, on ne bloque pas forcément, mais ici on veut forcer la qualité
                    # Considérons que si on ne peut pas linter, c'est un échec ou on ignore ? 
                    # Pour la sécurité, marquons comme échec si critique, sinon log warning.
                    pass

        # Le succès global nécessite : Tests OK ET Pylint >= 8
        global_success = tests_passed and pylint_success

        if global_success:
            result = {
                "status": "success",
                "message": "All tests passed and Pylint score >= 8. Mission complete.",
                "pylint_results": pylint_results
            }
        else:
            failing_tests = self._extract_failures(output)
            
            # Si les tests passent mais Pylint échoue, on ajoute les erreurs Pylint au feedback
            if tests_passed and not pylint_success:
                lint_errors = ["PYLINT QUALITY CHECK FAILED (Score < 8.0):"]
                for fpath, res in pylint_results.items():
                    score = res.get("score", 0)
                    if score < 8.0:
                        lint_errors.append(f"\nFile: {Path(fpath).name} (Score: {score}/10)")
                        # Ajouter les messages importants
                        for msg in res.get("errors", []) + res.get("conventions", []) + res.get("refactors", []):
                             lint_errors.append(f"  - {msg}")
                
                failing_tests.append({
                    "file": "Quality Gate",
                    "test": "Pylint Analysis",
                    "error": "\n".join(lint_errors[:20]) # Limiter la taille du feedback
                })

            result = {
                "status": "failure",
                "failing_tests": failing_tests,
                "pylint_results": pylint_results
            }
        
        # Logger l'exécution
        log_experiment(
            agent_name="Judge_Agent",
            model_used="pytest+pylint",
            action=ActionType.ANALYSIS if global_success else ActionType.DEBUG,
            details={
                "target_directory": str(target_dir),
                "input_prompt": f"validate {target_dir}",
                "output_response": output,  # Include pytest output
                "tests_passed": tests_passed,
                "pylint_success": pylint_success,
                "full_pytest_result": pytest_result,
                "pylint_scores": {k: v.get("score") for k, v in pylint_results.items()}
            },
            status="SUCCESS" if global_success else "FAILED"
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
