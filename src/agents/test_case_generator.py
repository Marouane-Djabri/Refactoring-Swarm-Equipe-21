"""
TestCaseGenerator Agent - Génère des fichiers de test pour le sandbox via LLM
"""
import os
import re
from mistralai import Mistral
from typing import List
from dotenv import load_dotenv
from pathlib import Path
from src.utils.logger import log_experiment, ActionType

import re

class TestCaseGeneratorAgent:
    """
    Agent responsable de la génération des fichiers de test utilisant Mistral
    """
    def __init__(self, model_name: str = "mistral-large-latest"):
        self.model_name = model_name
        
        load_dotenv()
        api_key = os.getenv("MISTRAL_API_KEY")
        
        if not api_key:
            raise ValueError(
                "MISTRAL_API_KEY not found in .env! "
                "Create a .env file with your API key."
            )
            
        self.client = Mistral(api_key=api_key)
        print(f"TestCaseGenerator Agent initialized with model: {model_name}")

    def _clean_code(self, code: str) -> str:
        """
        Nettoie le code généré pour ne garder que le contenu brut sans markdown
        """
        if code.strip().startswith("```python"):
            code = code.strip()[len("```python"):].strip()
        elif code.strip().startswith("```"):
            code = code.strip()[3:].strip()
        
        if code.strip().endswith("```"):
            code = code.strip()[:-3].strip()
        
        return code

    def _load_prompts(self) -> dict:
        """
        Charge les prompts de génération depuis le fichier TXT.
        Attendu: Sections séparées par "--- filename ---"
        """
        prompts_path = Path(__file__).parent.parent / "prompts" / "test_case_generator_prompt.txt"
        if not prompts_path.exists():
            raise FileNotFoundError(f"Prompts file not found at {prompts_path}")
            
        content = prompts_path.read_text(encoding="utf-8")
        prompts = {}
        
        # Regex pour capturer "--- filename ---" suivi du contenu
        matches = re.split(r"--- (.*?) ---\s*", content)
        # re.split retourne [preamble, filename1, content1, filename2, content2, ...]
        
        # On ignore le premier élément (preamble vide ou texte avant le premier header)
        for i in range(1, len(matches), 2):
            filename = matches[i].strip()
            prompt_text = matches[i+1].strip()
            if filename and prompt_text:
                prompts[filename] = prompt_text
                
        return prompts

    def generate_tests(self, target_dir: str):
        """
        Génère 3 types de fichiers de test dans le dossier cible via LLM
        """
        print ("generate tests called")
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        # Vérifier si des fichiers Python existent déjà
        existing_files = list(target_path.glob("*.py"))
        if existing_files:
            print(f"✅ Existing Python files found in {target_dir}. Skipping generation.")
            log_experiment(
                agent_name="TestCaseGenerator_Agent",
                model_used="None",
                action=ActionType.GENERATION,
                details={
                    "target_directory": str(target_dir),
                    "input_prompt": "Check for existing files",
                    "output_response": f"Skipped generation. Found: {[f.name for f in existing_files]}",
                    "status": "SKIPPED"
                },
                status="SUCCESS"
            )
            return
        
        prompts_map = self._load_prompts()
        
        generated_files = []
        full_response_log = ""

        print("\nTestCaseGenerator: Generating files via LLM...")

        for filename, prompt in prompts_map.items():
            try:
                response = self.client.chat.complete(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}]
                )
                code_content = self._clean_code(response.choices[0].message.content)
                
                file_path = target_path / filename
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(code_content)
                
                generated_files.append(filename)
                full_response_log += f"File {filename}: {len(code_content)} chars generated.\n"
                print(f"   • Generated {filename}")
                
            except Exception as e:
                print(f"❌ Error generating {filename}: {e}")
                full_response_log += f"File {filename}: ERROR {e}\n"

        log_experiment(
            agent_name="TestCaseGenerator_Agent",
            model_used=self.model_name,
            action=ActionType.GENERATION,
            details={
                "target_directory": str(target_dir),
                "generated_files": generated_files,
                "input_prompt": "Generate 3 test files (syntax_error, logic_bug, bad_code) via LLM",
                "output_response": full_response_log
            },
            status="SUCCESS" if len(generated_files) == 3 else "PARTIAL_SUCCESS"
        )

