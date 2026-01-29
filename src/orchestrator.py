"""
Orchestrator - Gère le flux d'exécution des agents
Test-generator -> Auditor -> Fixer -> Judge en boucle
"""

from pathlib import Path
from typing import Dict, List, TypedDict, Annotated, Optional
import operator

from langgraph.graph import StateGraph, END

from src.agents.auditor import AuditorAgent
from src.agents.fixer import FixerAgent
from src.agents.judge import JudgeAgent
from src.agents.test_generator import TestGeneratorAgent
from src.tools.refactoring_tools import RefactoringTools
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

    # Outils partagés
    tools: RefactoringTools

    # Résultats de l'Auditor
    refactoring_plan: Dict
    audit_completed: bool

    # Indicateur pour TestGenerator
    tests_generated: bool

    # Résultats du Fixer
    fix_results: Dict
    fix_completed: bool
    current_iteration: int
    
    # Feedback du Judge
    tests_passed: bool
    test_results: Dict
    error_feedback: Optional[str]
    should_continue: bool
    max_iterations: int

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

    def __init__(self, max_iterations: int = 10, model_name: str = "mistral-large-latest", target_dir: str = "./sandbox"):
        """
        Initialise l'orchestrateur LangGraph
        """
        self.max_iterations = max_iterations
        self.model_name = model_name

        print("=" * 30)
        print("INITIALISATION DU REFACTORING SWARM avec LangGraph")
        print("=" * 30)

        # Initialiser les outils
        print(f"\n🔧 Initializing RefactoringTools...")
        self.tools = RefactoringTools(base_sandbox=target_dir)
        self.sandbox_info = self.tools.get_sandbox_info()
        print(f"   ✅ Sandbox: {self.sandbox_info['sandbox_path']}")
        print(
            f"   ✅ Python files in sandbox: {self.sandbox_info['total_python_files']}")
        print(f"   ✅ Test files: {self.sandbox_info['test_files']}")
        print(
            f"   ✅ Backups available: {self.sandbox_info['backups_available']}")

        # Initialiser les 3 agents
        self.auditor = AuditorAgent(model_name=model_name)
        self.fixer = FixerAgent(model_name=model_name)
        self.judge = JudgeAgent(model_name=model_name)
        self.test_generator = TestGeneratorAgent(model_name=model_name)

        # Créer le graphe d'exécution
        self.workflow = self._build_workflow_graph()

        print("\nGraphe LangGraph créé!")
        print("Noeuds: Auditor -> TestGenerator -> Judge -> Fixer -> (Loop to Judge)")
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

        # Noeud 2.5: TestGenerator (generation de tests unitaires)
        workflow.add_node("test_generator", self._test_generator_node)

        # Noeud 3: Judge (test et validation)
        workflow.add_node("judge", self._judge_node)

        # ===== DÉFINIR LES TRANSITIONS =====

        # START -> Auditor (toujours commencer par l'analyse)
        workflow.set_entry_point("auditor")

        # Auditor -> TestGenerator (plans -> tests)
        workflow.add_edge("auditor", "test_generator")
        
        # TestGenerator -> Judge (tests -> validation initiale)
        workflow.add_edge("test_generator", "judge")

        # Judge -> ? (transition conditionnelle)
        workflow.add_conditional_edges(
            "judge",
            self._should_continue_or_stop,  
            {
                "continue": "fixer",  # Si échec -> Fixer
                "stop": END           # Si succès -> Fin
            }
        )

        # Fixer -> Judge (correction -> re-validation)
        workflow.add_edge("fixer", "judge")

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

        # Exécuter l'analyse
        refactoring_plan = self.auditor.analyze(Path(state["target_dir"]))

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
        print(
            f"NOEUD: FIXER (Correction - Iteration {state['current_iteration']})")
        print("=" * 30)

        refactoring_plan = state["refactoring_plan"]
        iteration = state["current_iteration"]

        # Exécuter la correction
        fix_results = self.fixer.fix_code(
            refactoring_plan, test_errors=state.get("error_feedback"))

        # Mettre à jour l'état
        state["fix_results"] = fix_results
        state["fix_completed"] = True
        # Note: current_iteration est incrémenté dans _should_continue_or_stop

        return state

    def _test_generator_node(self, state: RefactoringState) -> RefactoringState:
        """
        Noeud TestGenerator: Génère des tests unitaires pour le code (une seule fois)
        """
        
        # Si les tests ont déjà été générés, on passe (le graphe ne devrait pas repasser par ici, mais sécurité)
        if state.get("tests_generated"):
            print("\n" + "=" * 30)
            print("NOEUD: TEST GENERATOR (Skipped - Already Generated)")
            print("=" * 30)
            return state

        print("\n" + "=" * 30)
        print("NOEUD: TEST GENERATOR (Test Creation)")
        print("=" * 30)
        
        target_dir = state["target_dir"]
        self.test_generator.generate_unit_tests(target_dir)
        
        state["tests_generated"] = True
        return state
        
    def _judge_node(self, state: RefactoringState) -> RefactoringState:
        """
        Noeud Judge: Teste et valide le code corrigé
        """
        print("\n" + "=" * 30)
        print("NOEUD: JUDGE (Test and Validation)")
        print("=" * 30)

        target_dir = Path(state["target_dir"])

        # Exécuter les tests
        test_results = self.judge.run_tests(target_dir)

        # Mettre à jour l'état
        state["test_results"] = test_results
        state["tests_passed"] = test_results.get("status") == "success"

        # Si tests échouent, préparer le feedback pour le prochain cycle
        if not state["tests_passed"]:
            # Recupérer uniquement les tests echoués
            failing_tests = test_results.get("failing_tests", [])
            
            # Formater le feedback avec SEULEMENT les tests echoués
            feedback_messages = []
            if failing_tests:
                feedback_messages.append("TEST FAILURES (Fix these SPECIFIC errors):")
                for failure in failing_tests:
                    feedback_messages.append(f"""
- File: {failure.get('file', 'unknown')}
- Test: {failure.get('test', 'unknown')}
- Error: {failure.get('error', 'No error message')}
""")
            
            # Si on a des erreurs Pylint (stockées dans failing_tests pour le moment par JudgeAgent)
            # Elles seront incluses car _extract_failures les gère ou Judge les y met
            
            state["error_feedback"] = "\n".join(feedback_messages)
            
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
            print(f"\\nDECISION: STOP (Tests successful)")
            state["should_continue"] = False
            return "stop"

        elif current_iteration >= max_iterations:
            # Max itérations atteint -> Échec
            print(f"\nDECISION: STOP (Max iterations: {max_iterations})")
            state["should_continue"] = False
            return "stop"

        else:
            # Continuer le loop
            print(
                f"\nDECISION: CONTINUE (Iteration {current_iteration + 1}/{max_iterations})")
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

        print(f"Python files discovered: {len(python_files)}")
        for f in python_files:
            print(f"   • {f.relative_to(target_dir)}")

        return python_files

    def validate_sandbox(self, target_dir: str) -> bool:
        """
        Valide que le répertoire cible est accessible et contient des fichiers
        """
        validation = self.tools.validate_target_dir(target_dir)

        if not validation.get("valid"):
            print(f"❌ Erreur: {validation.get('error')}")
            return False

        print(f"✅ Sandbox validated: {validation.get('relative_path')}")
        return True

    def run(self, target_dir: str) -> Dict:
        """
        Point d'entrée principal: exécute le graphe LangGraph
        """
        target_path = Path(target_dir)

        # Validation du répertoire
        if not target_path.exists():
            error_msg = f"Erreur: The directory '{target_dir}' does not exist!"
            print(error_msg)
            return {"success": False, "error": error_msg}

        print(f"Target directory: {target_path.absolute()}\n")

        # Découvrir les fichiers Python
        python_files = self.discover_python_files(target_path)

        if not python_files:
            print("No Python files found initially.")

        # ===== INITIALISER L'ÉTAT =====
        initial_state: RefactoringState = {
            "target_dir": str(target_path),
            "python_files": python_files,
            "tools": self.tools,
            "refactoring_plan": {},
            "audit_completed": False,
            "tests_generated": False,
            "fix_results": {},
            "fix_completed": False,
            "current_iteration": 1,
            "test_results": {},
            "tests_passed": False,
            "error_feedback": None,
            "max_iterations": self.max_iterations,
            "should_continue": True,
            "final_result": {}
        }

        print("\n" + "=" * 60)
        print("EXECUTION OF LANGGRAPH")
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
                print("SUCCESS: All tests pass!")
                print("=" * 30)
                print(f"   • Iterations needed: {iteration}")

                final_result = {
                    "success": True,
                    "iterations_needed": iteration,
                    "test_result": test_results
                }
            else:
                print("\n" + "=" * 30)
                print(
                    f"FAILURE: Max iterations reached ({self.max_iterations})")
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
                    "input_prompt": f"Orchestration LangGraph sur {len(python_files)} fichiers avec RefactoringTools",
                    "output_response": f"Succès: {tests_passed}, Itérations: {iteration}",
                    "total_files": len(python_files),
                    "max_iterations": self.max_iterations,
                    "final_result": final_result,
                    "graph_execution": "LangGraph workflow completed",
                    "tools_used": {
                        "sandbox_path": self.sandbox_info['sandbox_path'],
                        "backups_created": self.sandbox_info['backups_available'],
                        "test_files": self.sandbox_info['test_files']
                    }
                },
                status="SUCCESS" if tests_passed else "FAILED"
            )

            return final_result

        except Exception as e:
            print(f"\nError executing the graph: {e}")
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": str(e)
            }
