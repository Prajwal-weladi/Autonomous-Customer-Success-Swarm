"""
LLM client for policy evaluation agent.
"""
import json
import logging
from typing import Optional, Dict, Any

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logging.warning("Warning: ollama not available")


class PolicyLLMClient:
    """Client for LLM-based policy evaluation."""
    
    def __init__(
        self,
        model: str = "qwen2.5:0.5b",
        temperature: float = 0.1,
        base_url: str = "http://localhost:11434"
    ):
        self.model = model
        self.temperature = temperature
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
        
        if OLLAMA_AVAILABLE:
            self.logger.info(f"PolicyLLMClient initialized with model '{model}'")
        else:
            self.logger.warning("Ollama not available, policy evaluation will not work")
    
    def evaluate(
        self,
        prompt: str
    ) -> Dict[str, Any]:
        """
        Evaluate a policy request using LLM.
        
        Args:
            prompt: The evaluation prompt
            
        Returns:
            Dictionary with evaluation result
        """
        if not OLLAMA_AVAILABLE:
            self.logger.error("Ollama not available")
            return {
                "allowed": False,
                "reason": "Policy evaluation service unavailable",
                "error": "Ollama not available"
            }
        
        try:
            self.logger.debug(f"Calling LLM model '{self.model}' for policy evaluation")
            
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": self.temperature}
            )
            
            output = response.get("message", {}).get("content", "")
            self.logger.debug(f"LLM response: {output[:200]}...")
            
            # Try to parse JSON response
            try:
                # Clean up potential markdown formatting
                if "```json" in output:
                    output = output.split("```json")[1].split("```")[0].strip()
                elif "```" in output:
                    output = output.split("```")[1].split("```")[0].strip()
                
                result = json.loads(output)
                
                # Validate required fields
                if "allowed" not in result or "reason" not in result:
                    self.logger.warning("LLM response missing required fields")
                    return {
                        "allowed": False,
                        "reason": "Unable to evaluate policy at this time",
                        "policy_type": result.get("policy_type"),
                        "error": "Invalid LLM response format"
                    }
                
                return result
                
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.error(f"Failed to parse LLM output as JSON: {e}")
                self.logger.debug(f"Raw output: {output[:500]}")
                return {
                    "allowed": False,
                    "reason": f"Policy evaluation failed: {str(e)}",
                    "error": "JSON parse error"
                }
                
        except Exception as e:
            self.logger.error(f"LLM policy evaluation failed: {e}", exc_info=True)
            return {
                "allowed": False,
                "reason": f"Policy evaluation error: {str(e)}",
                "error": str(e)
            }
