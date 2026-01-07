"""
Orchestrator - Gère le flux d'exécution des agents
Auditor -> Fixer -> Judge en boucle
"""

from pathlib import Path
from typing import Dict, List, TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, END

from src.agents.auditor import AuditorAgent
from src.agents.fixer import FixerAgent
from src.agents.judge import JudgeAgent
from src.utils.logger import log_experiment, ActionType


# Définir l'état du système (State Schema)
class RefactoringState(TypedDict):
    """
    État partagé entre tous les agents dans le graphe LangGraph

    Cet état est passé de noeud en noeud et peut être modifié par chaque agent.
    """
    # Données d'entrée
    target_dir: str
    python_files: List[Path]
    
    # Résultats de l'Auditor
    refactoring_plan: Dict
    audit_completed: bool
    
    # Résultats du Fixer
    fix_results: Dict
    fix_completed: bool
    current_iteration: int
    
    # Résultats du Judge
    test_results: Dict
    tests_passed: bool
    error_feedback: str
    
    # Métadonnées
    max_iterations: int
    should_continue: bool
    final_result: Dict


class LangGraphOrchestrator:
    """
    Orchestrateur basé sur LangGraph pour gérer le workflow multi-agents
    """
    
    def __init__(self, max_iterations: int = 10, model_name: str = "gemini-2.5-flash"):
        """
        Initialise l'orchestrateur LangGraph
        """
        self.max_iterations = max_iterations
        self.model_name = model_name
        
        print("=" * 30)
        print("INITIALISATION DU REFACTORING SWARM avec LangGraph")
        print("=" * 30)
        
        # Initialiser les 3 agents
        self.auditor = AuditorAgent(model_name=model_name)
        self.fixer = FixerAgent(model_name=model_name)
        self.judge = JudgeAgent(model_name=model_name)
        
        # Créer le graphe d'exécution
        self.workflow = self._build_workflow_graph()
        
        print("\nGraphe LangGraph créé!")
        print("Noeuds: Auditor -> Fixer -> Judge -> (Loop)")
        print()
    
    def _build_workflow_graph(self) -> StateGraph:
        """
        Construit le graphe d'exécution avec LangGraph
        """
        # Créer un nouveau graphe d'états
        workflow = StateGraph(RefactoringState)
        
        # ===== DÉFINIR LES NOEUDS =====
        
        # Noeud 1: Auditor (analyse)
        workflow.add_node("auditor", self._auditor_node)
        
        # Noeud 2: Fixer (correction)
        workflow.add_node("fixer", self._fixer_node)
        
        # Noeud 3: Judge (test et validation)
        workflow.add_node("judge", self._judge_node)
        
        # ===== DÉFINIR LES TRANSITIONS =====
        
        # START -> Auditor (toujours commencer par l'analyse)
        workflow.set_entry_point("auditor")
        
        # Auditor -> Fixer (après analyse, toujours corriger)
        workflow.add_edge("auditor", "fixer")
        
        # Fixer -> Judge (après correction, toujours tester)
        workflow.add_edge("fixer", "judge")
        
        # Judge -> ? (transition conditionnelle)
        workflow.add_conditional_edges(
            "judge",
            self._should_continue_or_stop,  # Fonction de décision
            {
                "continue": "fixer",  # Si tests échouent et < max_iter -> Fixer
                "stop": END           # Si tests OK ou max_iter atteint -> Fin
            }
        )
        
        # Compiler le graphe
        app = workflow.compile()
        
        return app
    
    # ===== FONCTIONS DES NOEUDS =====
    
    def _auditor_node(self, state: RefactoringState) -> RefactoringState:
        """
        Noeud Auditor: Analyse tous les fichiers Python
        """
        print("\n" + "=" * 30)
        print("NOEUD: AUDITOR (Analyse)")
        print("=" * 30)
        
        python_files = state["python_files"]
        
        # Exécuter l'analyse
        refactoring_plan = self.auditor.analyze(python_files)
        
        # Mettre à jour l'état
        state["refactoring_plan"] = refactoring_plan
        state["audit_completed"] = True
        state["current_iteration"] = 1
        
        return state
    
    def _fixer_node(self, state: RefactoringState) -> RefactoringState:
        """
        Noeud Fixer: Corrige le code selon le plan
        """
        print("\n" + "=" * 30)
        print(f"NOEUD: FIXER (Correction - Itération {state['current_iteration']})")
        print("=" * 30)
        
        refactoring_plan = state["refactoring_plan"]
        iteration = state["current_iteration"]
        
        # Exécuter la correction
        fix_results = self.fixer.fix_code(refactoring_plan, iteration=iteration)
        
        # Mettre à jour l'état
        state["fix_results"] = fix_results
        state["fix_completed"] = True
        
        return state
    
    def _judge_node(self, state: RefactoringState) -> RefactoringState:
        """
        Noeud Judge: Teste et valide le code corrigé
        """
        print("\n" + "=" * 30)
        print("NOEUD: JUDGE (Test et Validation)")
        print("=" * 30)
        
        target_dir = Path(state["target_dir"])
        
        # Exécuter les tests
        test_results = self.judge.run_tests(target_dir)
        
        # Mettre à jour l'état
        state["test_results"] = test_results
        state["tests_passed"] = test_results.get("success", False)
        
        # Si tests échouent, préparer le feedback pour le prochain cycle
        if not state["tests_passed"]:
            state["error_feedback"] = test_results.get("pytest_output", "No error details")
            # Injecter les erreurs dans le plan pour le Fixer
            state["refactoring_plan"]["errors"] = state["error_feedback"]
        
        return state
    
    # ===== FONCTION DE DÉCISION =====
    
    def _should_continue_or_stop(self, state: RefactoringState) -> str:
        """
        Décide si on continue le loop ou si on s'arrête
        
        Cette fonction est appelée après le noeud Judge pour déterminer
        la prochaine étape.
        """
        tests_passed = state["tests_passed"]
        current_iteration = state["current_iteration"]
        max_iterations = state["max_iterations"]
        
        if tests_passed:
            # Tous les tests passent -> Succès!
            print(f"\nDÉCISION: STOP (Tests réussis)")
            state["should_continue"] = False
            return "stop"
        
        elif current_iteration >= max_iterations:
            # Max itérations atteint -> Échec
            print(f"\nDÉCISION: STOP (Max itérations: {max_iterations})")
            state["should_continue"] = False
            return "stop"
        
        else:
            # Continuer le loop
            print(f"\nDÉCISION: CONTINUE (Itération {current_iteration + 1}/{max_iterations})")
            state["current_iteration"] += 1
            state["should_continue"] = True
            return "continue"
    
    # ===== MÉTHODE PRINCIPALE =====
    
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
        Point d'entrée principal: exécute le graphe LangGraph
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
        
        # ===== INITIALISER L'ÉTAT =====
        initial_state: RefactoringState = {
            "target_dir": str(target_path),
            "python_files": python_files,
            "refactoring_plan": {},
            "audit_completed": False,
            "fix_results": {},
            "fix_completed": False,
            "current_iteration": 1,
            "test_results": {},
            "tests_passed": False,
            "error_feedback": "",
            "max_iterations": self.max_iterations,
            "should_continue": True,
            "final_result": {}
        }
        
        print("\n" + "=" * 60)
        print("EXÉCUTION DU GRAPHE LANGGRAPH")
        print("=" * 60)
        
        # ===== EXÉCUTER LE GRAPHE =====
        try:
            # Invoquer le graphe avec l'état initial
            final_state = self.workflow.invoke(initial_state)
            
            # Construire le résultat final
            tests_passed = final_state["tests_passed"]
            iteration = final_state["current_iteration"]
            test_results = final_state["test_results"]
            
            if tests_passed:
                print("\n" + "=" * 30)
                print("SUCCÈS: Tous les tests passent!")
                print("=" * 30)
                print(f"   • Itérations nécessaires: {iteration}")
                print(f"   • Couverture: {test_results.get('coverage', {}).get('coverage_percent', 'N/A')}%")
                print(f"   • Score Pylint: {test_results.get('pylint_result', {}).get('score', 'N/A')}/10")
                
                final_result = {
                    "success": True,
                    "iterations_needed": iteration,
                    "final_coverage": test_results.get('coverage', {}).get('coverage_percent', 0),
                    "final_pylint_score": test_results.get('pylint_result', {}).get('score', 0),
                    "test_result": test_results
                }
            else:
                print("\n" + "=" * 30)
                print(f"ÉCHEC: Limite d'itérations atteinte ({self.max_iterations})")
                print("=" * 30)

                final_result = {
                    "success": False,
                    "iterations_needed": self.max_iterations,
                    "reason": "Max iterations reached",
                    "last_test_result": test_results
                }
            
            # Logger le résultat final
            log_experiment(
                agent_name="LangGraph_Orchestrator",
                model_used=self.model_name,
                action=ActionType.ANALYSIS,
                details={
                    "target_directory": str(target_path),
                    "input_prompt": f"Orchestration LangGraph sur {len(python_files)} fichiers",
                    "output_response": f"Succès: {tests_passed}, Itérations: {iteration}",
                    "total_files": len(python_files),
                    "max_iterations": self.max_iterations,
                    "final_result": final_result,
                    "graph_execution": "LangGraph workflow completed"
                },
                status="SUCCESS" if tests_passed else "FAILED"
            )
            
            return final_result
            
        except Exception as e:
            print(f"\nErreur lors de l'exécution du graphe: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "error": str(e)
            }