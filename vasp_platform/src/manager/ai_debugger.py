
import json
import logging
from typing import Dict, Any, Optional
from vasp_platform.src.core.llm import GoogleGenAIAdapter

class AIDebugger:
    """
    Uses Google Gemini to analyze VASP error logs and suggest INCAR modifications.
    """
    
    def __init__(self):
        self.llm = GoogleGenAIAdapter(model_name='gemini-2.0-flash-thinking-exp-01-21')

    def analyze(self, run_log: str, outcar_tail: str, incar_content: str) -> Dict[str, Any]:
        """
        Analyzes the provided logs and returns a dictionary of INCAR tags to update.
        
        Args:
            run_log: The last ~100 lines of run.log (stdout).
            outcar_tail: The last ~100 lines of OUTCAR.
            incar_content: The current content of the INCAR file.
            
        Returns:
            Dict: A dictionary where keys are INCAR tags and values are the new values.
                  Returns empty dict if no clear fix is found.
        """
        prompt = f"""
        You are a Density Functional Theory (DFT) Expert and VASP Specialist.
        A VASP calculation has failed. Your task is to analyze the logs and determine the specific INCAR parameters that must be changed to fix the error.

        CONTEXT:
        --- CURRENT INCAR ---
        {incar_content}
        ---------------------

        --- RUN.LOG (STDOUT) ---
        {run_log}
        ------------------------

        --- OUTCAR (TAIL) ---
        {outcar_tail}
        ---------------------

        INSTRUCTIONS:
        1. Identify the fatal error (e.g., ZHEGV, EDDDAV, FEXCP, unrelated to algorithm).
        2. Determine the corrective action for the INCAR file.
        3. Return ONLY a valid JSON object containing the INCAR tags to be updated or added.
        4. Do NOT verify, explain, or add markdown formatting. Just the JSON.
        
        Example Output:
        {{"ALGO": "Normal", "ISMEAR": 0, "SIGMA": 0.05}}
        """

        try:
            response_text = self.llm.generate(prompt)
            # Cleanup JSON (remove markdown code blocks if LLM adds them)
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            fixes = json.loads(cleaned_text)
            
            if not isinstance(fixes, dict):
                print(f"[AIDebugger] LLM returned non-dict JSON: {cleaned_text}")
                return {}
                
            return fixes
            
        except json.JSONDecodeError:
            print(f"[AIDebugger] Failed to parse JSON from LLM: {response_text}")
            return {}
        except Exception as e:
            print(f"[AIDebugger] Error during analysis: {e}")
            return {}
