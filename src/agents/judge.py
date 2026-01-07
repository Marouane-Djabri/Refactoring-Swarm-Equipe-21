"""
Judge Agent - Exécute les tests et valide le code corrigé
"""

import os
from pathlib import Path
from typing import Dict, List

# import google.generativeai as genai
# from dotenv import load_dotenv

from src.tools.test_tools import run_pytest, check_test_coverage
from src.tools.analysis_tools import run_pylint
from src.utils.logger import log_experiment, ActionType


class JudgeAgent:
    """
    Agent responsable de la validation du code par tests
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """
        Initialise l'agent Judge
        """
        self.model_name = model_name
        
        # TODO: Configuration API
        # load_dotenv()
        # api_key = os.getenv("GOOGLE_API_KEY")
        # 
        # if not api_key:
        #     raise ValueError(
        #         "GOOGLE_API_KEY non trouvée dans .env! "
        #         "Créez un fichier .env avec votre clé API."
        #     )
        # 
        # genai.configure(api_key=api_key)
        # self.model = genai.GenerativeModel(model_name)
        
        print(f"Judge Agent initialisé")
    
    def check_pylint_quality(self, target_dir: Path) -> Dict:
        """
        Vérifie la qualité du code avec pylint
        """
        print(f"Vérification qualité pylint...")
        
        pylint_result = run_pylint(target_dir)
        return pylint_result
    
    def run_tests(self, target_dir: Path) -> Dict:
        """
        Exécute les tests unitaires avec pytest
        """
        print(f"\nJudge: Exécution des tests...")
        
        pytest_result = run_pytest(target_dir)

        # Extraire les données
        all_tests_passed = pytest_result["success"]
        pytest_output = pytest_result["output"]
        
        # Vérifier la couverture de tests
        coverage_result = check_test_coverage(target_dir)

        # Vérifier aussi la qualité du code (pylint)
        pylint_result = self.check_pylint_quality(target_dir)
        
        # Logger l'exécution des tests
        log_experiment(
            agent_name="Judge_Agent",
            model_used="pytest",  # Pas vraiment un LLM ici
            action=ActionType.DEBUG if all_tests_passed else ActionType.ANALYSIS,
            details={
                "target_directory": str(target_dir),
                "input_prompt": f"Exécution pytest sur {target_dir}",  # OBLIGATOIRE
                "output_response": pytest_output,
                "all_tests_passed": all_tests_passed,
                "test_coverage": coverage_result.get("coverage_percent", 0),
                "pylint_score": pylint_result.get("score", 0),
                "pylint_improved": pylint_result.get("improved", False)
            },
            status="SUCCESS" if all_tests_passed else "FAILED"
        )
        
        # Construire le résultat
        result = {
            "success": all_tests_passed,
            "pytest_output": pytest_output,
            "coverage": coverage_result,
            "pylint_result": pylint_result,
            "quality_improved": pylint_result.get("improved", False)
        }
        
        # Affichage des résultats
        if all_tests_passed:
            print(f"Tous les tests passent!")
            print(f"Couverture: {coverage_result.get('coverage_percent', 'N/A')}%")
            print(f"Score pylint: {pylint_result.get('score', 'N/A')}")
        else:
            print(f"Tests échoués - Logs envoyés au Fixer")
            print(f"Couverture: {coverage_result.get('coverage_percent', 'N/A')}%")
        
        return result
