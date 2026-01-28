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
    # Run the orchestrator
    try:
        print("\n[Orchestrator] Starting Refactoring Swarm...")
        orchestrator = LangGraphOrchestrator()
        orchestrator.run(args.target_dir)
    except Exception as e:
        print(f"❌ Orchestrator failed: {e}")
        sys.exit(1)

    print("✅ MISSION_COMPLETE")

if __name__ == "__main__":
    main()