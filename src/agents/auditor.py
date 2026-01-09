"""
Auditor Agent - Analyse le code et produit un plan de refactoring
"""

import os
from pathlib import Path
from typing import List, Dict
import json

import google.generativeai as genai
from dotenv import load_dotenv

from src.tools.file_operations import read_file, list_files
from src.tools.analysis_tools import run_pylint
from src.utils.logger import log_experiment, ActionType

class AuditorAgent:
    """
    Agent responsable de l'audit du code source
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """
        Initialise l'agent Auditor
        """
        self.model_name = model_name
        
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found in .env! "
                "Create a .env file with your API key."
            )
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        print(f"Auditor Agent initialised with the model: {model_name}")

    def _load_prompt(self) -> str:
        """
        Charge le prompt Auditor depuis le fichier .txt
        """
        prompt_path = (
            Path(__file__).resolve()
            .parent.parent / "prompts" / "auditor_prompt.txt"
        )

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"auditor_prompt.txt not found in: {prompt_path}"
            )

        return prompt_path.read_text(encoding="utf-8")
    
    def analyze(self, target_dir: Path) -> Dict:
        """
        Global audit of a target directory (sandbox)
        """
        print(f"\nAuditor: Analysis of {len(target_dir)} files...")

        prompt_template = self._load_prompt()

        files = list_files(target_dir)
        python_files = [f for f in files if f.endswith(".py")]

        analyses = []

        for file_path in python_files:
            content = read_file(file_path)
            pylint_report = run_pylint(file_path)

            analyses.append(
                {
                    "file": file_path,
                    "code_preview": content[:1000] + "..." if len(content) > 1000 else content,
                    "code_length": len(content),
                    "pylint": pylint_report,
                }
            )

        full_prompt = (
            f"{prompt_template}\n\n"
            f"PROJECT FILES ANALYSIS:\n"
            f"{json.dumps(analyses, indent=2)}"
        )

        response = self.model.generate_content(full_prompt)
        llm_response = response.text

        try:
            result = json.loads(llm_response)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM response is not valid JSON") from exc

        log_experiment(
            agent_name="Auditor_Agent",
            model_used=self.model_name,
            action=ActionType.ANALYSIS,
            details={
                "target_directory": str(target_dir),
                "files_analyzed": len(python_files),
                "input_prompt": full_prompt[:1500] + "..." if len(full_prompt) > 1500 else full_prompt,
                "output_response": llm_response[:1000] + "..." if len(llm_response) > 1000 else llm_response,
                "analysis_result_keys": list(result.keys()) if isinstance(result, dict) else []
            },
            status="SUCCESS",
        )

        return result
