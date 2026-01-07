"""
Orchestrator - Gère le flux d'exécution des agents
Auditor -> Fixer -> Judge en boucle
"""

from pathlib import Path
from typing import Dict, List
import time

from src.agents.auditor import AuditorAgent
from src.agents.fixer import FixerAgent
from src.agents.judge import JudgeAgent
from src.utils.logger import log_experiment, ActionType

class Orchestrator:
    """
    Chef d'orchestre du système multi-agents
    Gère le Self-Healing Loop: Auditor -> Fixer -> Judge -> (si échec) -> Fixer...
    """
    
    def __init__(self, max_iterations: int = 10, model_name: str = "gemini-2.5-flash"):
        """
        Initialise l'orchestrateur
        """
        self.max_iterations = max_iterations
        self.model_name = model_name
        
        # Initialiser les 3 agents
        print("=" * 30)
        print("INITIALISATION DU REFACTORING SWARM")
        print("=" * 30)
        
        self.auditor = AuditorAgent(model_name=model_name)
        self.fixer = FixerAgent(model_name=model_name)
        self.judge = JudgeAgent(model_name=model_name)
        
        print("\nTous les agents sont prêts!\n")
    
    def discover_python_files(self, target_dir: Path) -> List[Path]:
        """
        Découvre tous les fichiers Python dans le répertoire cible
        """
        python_files = list(target_dir.rglob("*.py"))
        
        # Filtrer les fichiers de test et __init__.py
        python_files = [
            f for f in python_files 
            if not f.name.startswith("test_") and f.name != "__init__.py"
        ]
        
        print(f"Fichiers Python découverts: {len(python_files)}")
        for f in python_files:
            print(f"   • {f.relative_to(target_dir)}")
        
        return python_files
    
    def run(self, target_dir: str) -> Dict:
        """
        Point d'entrée principal: exécute tout le pipeline
        """
        target_path = Path(target_dir)
        
        # Validation du répertoire
        if not target_path.exists():
            error_msg = f"Erreur: Le répertoire '{target_dir}' n'existe pas!"
            print(error_msg)
            return {"success": False, "error": error_msg}
        
        print(f"Répertoire cible: {target_path.absolute()}\n")
        
        # Découvrir les fichiers Python
        python_files = self.discover_python_files(target_path)
        
        if not python_files:
            print("Aucun fichier Python trouvé!")
            return {"success": False, "error": "No Python files found"}
        
        # ===== PHASE 1: AUDIT =====
        print("\n" + "=" * 30)
        print("PHASE 1: AUDIT DU CODE")
        print("=" * 30)
        
        refactoring_plan = self.auditor.analyze(python_files)
        
        # ===== SELF-HEALING LOOP =====
        print("\n" + "=" * 30)
        print("DÉMARRAGE DU SELF-HEALING LOOP")
        print("=" * 30)
        
        iteration = 1
        all_tests_passed = False
        final_result = None
        
        while iteration <= self.max_iterations and not all_tests_passed:
            print(f"\n{'─' * 30}")
            print(f"ITÉRATION {iteration}/{self.max_iterations}")
            print(f"{'─' * 30}")
            
            # ===== PHASE 2: CORRECTION =====
            print(f"\nPhase 2.{iteration}: CORRECTION DU CODE")
            fix_result = self.fixer.fix_code(refactoring_plan, iteration=iteration)
            
            # Attendre un peu pour laisser les fichiers se stabiliser
            time.sleep(1)
            
            # ===== PHASE 3: VALIDATION =====
            print(f"\nPhase 3.{iteration}: VALIDATION PAR TESTS")
            test_result = self.judge.run_tests(target_path)
            
            # Vérifier si tous les tests passent
            all_tests_passed = test_result.get("success", False)
            
            if all_tests_passed:
                print("\n" + "=" * 30)
                print("SUCCÈS: Tous les tests passent!")
                print("=" * 30)
                print(f"   • Couverture: {test_result['coverage'].get('coverage_percent', 'N/A')}%")
                print(f"   • Score Pylint: {test_result['pylint_result'].get('score', 'N/A')}/10")
                print(f"   • Itérations nécessaires: {iteration}")
                
                final_result = {
                    "success": True,
                    "iterations_needed": iteration,
                    "final_coverage": test_result['coverage'].get('coverage_percent', 0),
                    "final_pylint_score": test_result['pylint_result'].get('score', 0),
                    "test_result": test_result
                }
                break
            else:
                print(f"\nTests échoués à l'itération {iteration}")
                print(f"Le Fixer va réessayer avec les logs d'erreur...")
                
                # Mettre à jour le plan avec les erreurs pour le prochain cycle
                refactoring_plan["errors"] = test_result.get("errors")
                
                iteration += 1
        
        # Si on a atteint le max d'itérations sans succès
        if not all_tests_passed:
            print("\n" + "=" * 30)
            print(f"ÉCHEC: Limite d'itérations atteinte ({self.max_iterations})")
            print("=" * 30)
            print("Le code n'a pas pu être entièrement corrigé.")
            
            final_result = {
                "success": False,
                "iterations_needed": self.max_iterations,
                "reason": "Max iterations reached",
                "last_test_result": test_result
            }
        
        # Logger le résultat final de l'orchestration
        log_experiment(
            agent_name="Orchestrator",
            model_used=self.model_name,
            action=ActionType.ANALYSIS,
            details={
                "target_directory": str(target_path),
                "input_prompt": f"Orchestration complète sur {len(python_files)} fichiers",
                "output_response": f"Succès: {all_tests_passed}, Itérations: {iteration-1 if all_tests_passed else self.max_iterations}",
                "total_files": len(python_files),
                "max_iterations": self.max_iterations,
                "final_result": final_result
            },
            status="SUCCESS" if all_tests_passed else "FAILED"
        )
        
        return final_result
