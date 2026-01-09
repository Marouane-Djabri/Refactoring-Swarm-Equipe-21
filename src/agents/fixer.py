"""
Fixer Agent - Corrige le code selon le plan de refactoring
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
import json

import google.generativeai as genai
from dotenv import load_dotenv

from src.tools.file_operations import read_file, write_file, backup_file
from src.tools.sandbox_security import validate_path
from src.utils.logger import log_experiment, ActionType

class FixerAgent:
    """
    Agent responsable de la correction du code source
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        """
        Initialise l'agent Fixer
        """
        self.model_name = model_name
        
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY non trouvée dans .env! "
                "Créez un fichier .env avec votre clé API."
            )
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        print(f"Fixer Agent initialisé avec le modèle: {model_name}")

    def _load_prompt(self) -> str:
        """
        Charge le prompt Fixer depuis le fichier .txt
        """
        prompt_path = (
            Path(__file__).resolve()
            .parent.parent / "prompts" / "fixer_prompt.txt"
        )

        if not prompt_path.exists():
            raise FileNotFoundError(
                f"fixer_prompt.txt not found in: {prompt_path}"
            )

        return prompt_path.read_text(encoding="utf-8")
    
    def _clean_generated_code(self, code: str) -> str:
        """
        Nettoie le code généré par le LLM (enlève les balises markdown)
        """
        # Enlever les balises markdown si présentes
        if code.strip().startswith("```python"):
            code = code.strip()[len("```python"):].strip()
        if code.strip().startswith("```"):
            code = code.strip()[3:].strip()
        if code.strip().endswith("```"):
            code = code.strip()[:-3].strip()
        
        return code
    
    def fix_code(self, refactoring_plan: Dict, test_errors: Optional[str] = None) -> Dict:
        """
        Corrige tous les fichiers selon le plan de refactoring
        """
        print(f"\nFixer: Correction...")

        issues: List[Dict] = refactoring_plan.get("issues", [])
        results = []

        prompt_template = self._load_prompt()
        
        # Corriger chaque issue
        for issue in issues:
            file_path = Path(issue["file"])
            validate_path(file_path)

            original_code = read_file(file_path)
            backup_file(file_path)

            prompt = (
                f"{prompt_template}\n\n"
                f"ISSUE TO FIX:\n"
                f"{json.dumps(issue, indent=2)}\n\n"
                f"CURRENT FILE CONTENT:\n"
                f"{original_code}\n\n"
            )

            response = self.model.generate_content(prompt)
            fixed_code = self._clean_generated_code(response.text)

            if fixed_code.strip() == original_code.strip():
                continue  # Nothing changed

            write_file(file_path, fixed_code)

            results.append(
                {
                    "file": str(file_path),
                    "description": issue["suggested_fix"],
                }
            )

            log_experiment(
                agent_name="Fixer_Agent",
                model_used=self.model_name,
                action=ActionType.DEBUG if test_errors else ActionType.FIX,
                details={
                    "input_prompt": prompt,
                    "output_response": response.text,
                    "file_fixed": str(file_path),
                },
                status="SUCCESS",
            )

        return {
            "results": results,
            "notes": (
                "Fixes applied strictly based on the Auditor plan "
                "and optional Judge error feedback."
                if results
                else "No changes were applied."
            ),
        }
