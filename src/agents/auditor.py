"""
Auditor Agent - Analyse le code et produit un plan de refactoring
"""

import os
from pathlib import Path
from typing import List, Dict
import json

from mistralai import Mistral
from dotenv import load_dotenv

from src.tools.file_operations import read_file, list_files
from src.tools.analysis_tools import run_pylint
from src.utils.logger import log_experiment, ActionType

class AuditorAgent:
    """
    Agent responsable de l'audit du code source
    """
    
    def __init__(self, model_name: str = "mistral-large-latest"):
        """
        Initialise l'agent Auditor
        """
        self.model_name = model_name
        
        load_dotenv()
        api_key = os.getenv("MISTRAL_API_KEY")
        
        if not api_key:
            raise ValueError(
                "MISTRAL_API_KEY not found in .env! "
                "Create a .env file with your API key."
            )
        
        self.client = Mistral(api_key=api_key)
        
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
        print(f"\nAuditor: Analysis of {len(str(target_dir) )} files...")

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

        response = self.client.chat.complete(
            model=self.model_name,
            messages=[{"role": "user", "content": full_prompt}],
            response_format={"type": "json_object"}
        )
        llm_response = response.choices[0].message.content

        # Nettoyage robuste de la réponse JSON (même avec le mode JSON, parfois utile)
        clean_response = llm_response.strip()
        
        # 1. Essayer d'extraire le bloc markdown
        if "```json" in clean_response:
            parts = clean_response.split("```json")
            if len(parts) > 1:
                clean_response = parts[1].split("```")[0].strip()
        elif "```" in clean_response:
             parts = clean_response.split("```")
             if len(parts) > 1:
                # Souvent le premier bloc est celui qui nous intéresse
                clean_response = parts[1].strip()

        # 2. Si ce n'est toujours pas propre, chercher les accolades extrêmes
        if not clean_response.startswith("{") and "{" in clean_response:
            start = clean_response.find("{")
            end = clean_response.rfind("}")
            if start != -1 and end != -1:
                clean_response = clean_response[start:end+1]

        try:
            result = json.loads(clean_response)
        except json.JSONDecodeError as exc:
             # Log the raw response for debugging
            print(f"FAILED JSON PARSING. Raw response:\n{llm_response}\nCleaned response:\n{clean_response}")
            raise ValueError(f"LLM response is not valid JSON: {exc}") from exc

        log_experiment(
            agent_name="Auditor_Agent",
            model_used=self.model_name,
            action=ActionType.ANALYSIS,
            details={
                "target_directory": str(target_dir),
                "files_analyzed": [str(p) for p in python_files],
                "input_prompt": full_prompt,
                "output_response": llm_response,
                "cleaned_response": clean_response,
                "issues_found": len(result.get("issues", [])) if isinstance(result, dict) else 0,
                "full_analysis_result": result
            },
            status="SUCCESS",
        )

        return result
