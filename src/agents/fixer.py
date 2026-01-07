"""
Fixer Agent - Corrige le code selon le plan de refactoring
"""

import os
from pathlib import Path
from typing import Dict

# import google.generativeai as genai
# from dotenv import load_dotenv

from src.tools.file_operations import read_file, write_file, backup_file
from src.tools.sandbox_security import validate_path
from src.prompts.fixer_prompts import FIX_PROMPT, SELF_HEAL_PROMPT
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
        
        # TODO: Configuration de l'API Gemini (comme dans Auditor)
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
        
        print(f"Fixer Agent initialisé avec le modèle: {model_name}")
    
    def fix_file(self, file_info: Dict, error_feedback: str = None) -> Dict:
        """
        Corrige un fichier individuel selon l'analyse et les retours d'erreur
        """
        file_path = Path(file_info["file"])
        print(f"Correction de: {file_path.name}")
        
        validate_path(file_path)  # Sécurité: vérifier qu'on reste dans sandbox
        original_code = read_file(file_path)
        backup_file(file_path)  # Sauvegarder avant modification

        # Construire le prompt selon la situation
        if error_feedback:
            # Mode Self-Healing: on a des erreurs de tests à corriger
            prompt = SELF_HEAL_PROMPT.format(
                code=original_code,
                issues=file_info.get("issues", "Non spécifié"),
                errors=error_feedback
            )
            action_type = ActionType.DEBUG  # C'est du debug car on corrige des erreurs
        else:
            # Mode initial: première correction basée sur l'analyse
            prompt = FIX_PROMPT.format(
                code=original_code,
                issues=file_info.get("issues", "Non spécifié")
            )
            action_type = ActionType.FIX  # C'est une correction/refactoring
        
        response = self.model.generate_content(prompt)
        fixed_code = response.text
        
        # Nettoyer le code généré (enlever les balises markdown si présentes)
        fixed_code = self._clean_generated_code(fixed_code)
        
        # Écrire le fichier corrigé:
        write_file(file_path, fixed_code)
        
        # Logger l'interaction
        log_experiment(
            agent_name="Fixer_Agent",
            model_used=self.model_name,
            action=action_type,  # FIX ou DEBUG selon le contexte
            details={
                "file_fixed": str(file_path),
                "input_prompt": prompt[:1000] + "..." if len(prompt) > 1000 else prompt,  # Tronquer si trop long
                "output_response": fixed_code[:500] + "..." if len(fixed_code) > 500 else fixed_code,
                "original_length": len(original_code),
                "fixed_length": len(fixed_code),
                "has_error_feedback": error_feedback is not None
            },
            status="SUCCESS"
        )
        
        return {
            "file": str(file_path),
            "success": True,
            "fixed_code": fixed_code
        }
    
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
    
    def fix_code(self, refactoring_plan: Dict, iteration: int = 1) -> Dict:
        """
        Corrige tous les fichiers selon le plan de refactoring
        """
        print(f"\nFixer: Correction (itération {iteration})...")
        
        files_to_fix = refactoring_plan.get("files_analyzed", [])
        error_feedback = refactoring_plan.get("errors", None)  # Erreurs du Judge
        
        results = []
        
        # Corriger chaque fichier
        for file_info in files_to_fix:
            # Si c'est une itération > 1, on a peut-être des erreurs spécifiques par fichier
            file_errors = None
            if error_feedback and isinstance(error_feedback, dict):
                file_errors = error_feedback.get(file_info.get("file"), None)
            elif error_feedback:
                file_errors = error_feedback  # Erreurs globales
            
            result = self.fix_file(file_info, file_errors)
            results.append(result)
        
        success_count = sum(1 for r in results if r.get("success", False))
        
        print(f"Fixer: {success_count}/{len(files_to_fix)} fichiers corrigés")
        
        return {
            "iteration": iteration,
            "total_files": len(files_to_fix),
            "successful_fixes": success_count,
            "results": results
        }
