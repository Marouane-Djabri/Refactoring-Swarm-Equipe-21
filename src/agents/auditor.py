"""
Auditor Agent - Analyse le code et produit un plan de refactoring
"""

import os
from pathlib import Path
from typing import List, Dict
import json

# import google.generativeai as genai
# from dotenv import load_dotenv

from src.tools.file_operations import read_file
from src.tools.analysis_tools import run_pylint
from src.prompts.auditor_prompts import ANALYSIS_PROMPT
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
        
        # TODO: configuration API:
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
        
        print(f"Auditor Agent initialisé avec le modèle: {model_name}")

    def analyze_file(self, file_path: Path) -> Dict:
        """
        Analyse un fichier Python individuel
        """
        print(f"Analyse de: {file_path.name}")
        
        code_content = read_file(file_path)
        pylint_result = run_pylint(file_path)
        
        analysis_prompt = ANALYSIS_PROMPT.format(
            code=code_content,
            pylint_issues=json.dumps(pylint_result.get("issues", []), indent=2)
        )
        
        response = self.model.generate_content(analysis_prompt)
        llm_response = response.text
        
        # Logger l'interaction avec le LLM
        log_experiment(
            agent_name="Auditor_Agent",
            model_used=self.model_name,
            action=ActionType.ANALYSIS,
            details={
                "file_analyzed": str(file_path),
                "input_prompt": analysis_prompt,
                "output_response": llm_response,
                "code_length": len(code_content),
                "pylint_score": pylint_result.get("score", 0),
                "issues_count": len(pylint_result.get("issues", []))
            },
            status="SUCCESS"
        )
        
        # Retourner les résultats structurés
        return {
            "file": str(file_path),
            "issues": llm_response,
            "pylint_score": pylint_result.get("score", 0),
            "pylint_issues": pylint_result.get("issues", []),
            "code_content": code_content
        }
    
    def analyze(self, python_files: List[Path]) -> Dict:
        """
        Analyse tous les fichiers et crée un plan de refactoring global
        """
        print(f"\nAuditor: Analyse de {len(python_files)} fichiers...")
        
        all_analyses = []
        
        # Analyser chaque fichier individuellement
        for file_path in python_files:
            analysis = self.analyze_file(file_path)
            all_analyses.append(analysis)
        
        # TODO: Le Prompt Engineer doit créer un prompt pour synthétiser
        # toutes les analyses individuelles en un plan global
        
        # Créer le plan de refactoring global
        refactoring_plan = {
            "total_files": len(python_files),
            "files_analyzed": all_analyses,
            "priority_files": [],  # Les fichiers les plus problématiques
            "global_issues": "À compléter avec l'analyse LLM",
            "recommended_order": [str(f) for f in python_files]  # Ordre de correction
        }
        
        # Utiliser le LLM pour prioriser les fichiers selon leur gravité
        synthesis_prompt = "Voici les analyses de tous les fichiers..."
        synthesis_response = self.model.generate_content(synthesis_prompt)
        
        print(f"Auditor: Plan créé pour {len(python_files)} fichiers")
        
        return refactoring_plan
