import argparse
import sys
import os
from dotenv import load_dotenv
from src.utils.logger import log_experiment, ActionType
from src.orchestrator import LangGraphOrchestrator

load_dotenv()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target_dir", type=str, required=True)
    args = parser.parse_args()

    if not os.path.exists(args.target_dir):
        print(f"❌ Dossier {args.target_dir} introuvable.")
        sys.exit(1)

    print(f"🚀 DEMARRAGE SUR : {args.target_dir}")
    log_experiment(
        agent_name="System",
        model_used="None",
        action=ActionType.ANALYSIS,
        details={
            "message": f"Target: {args.target_dir}",
            "input_prompt": f"CLI execution with target_dir={args.target_dir}",
            "output_response": "System startup initiated"
        },
        status="INFO"
    )

    # Run the orchestrator
    try:
        print("\n[Orchestrator] Starting Refactoring Swarm...")
        orchestrator = LangGraphOrchestrator()
        orchestrator.run(args.target_dir)
    except Exception as e:
        print(f"❌ Orchestrator failed: {e}")
        log_experiment(
            agent_name="Orchestrator",
            model_used="gemini",
            action=ActionType.DEBUG,
            details={
                "error": str(e),
                "input_prompt": "Run LangGraph Orchestrator",
                "output_response": f"Exception occurred: {str(e)}"
            },
            status="ERROR"
        )
        sys.exit(1)

    print("✅ MISSION_COMPLETE")

if __name__ == "__main__":
    main()