"""
Ollama LLM client for generation tasks.
"""
from typing import Optional, Dict, Any

from langchain_community.llms import Ollama

from app.core.config import settings
from app.core.logger import setup_logger


logger = setup_logger(__name__)


class OllamaClient:
    """Client for interacting with Ollama LLM."""
    
    def __init__(
        self,
        model: str = settings.GENERATION_MODEL,
        temperature: float = settings.GENERATION_TEMPERATURE,
        max_tokens: int = settings.GENERATION_MAX_TOKENS
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        self.llm = Ollama(
            model=model,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=temperature,
            num_predict=max_tokens
        )
        
        logger.info(
            f"Initialized OllamaClient with model '{model}', "
            f"temperature={temperature}, max_tokens={max_tokens}"
        )
    
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[list] = None
    ) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: Input prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stop: Stop sequences
        
        Returns:
            Generated text
        """
        try:
            # Create a new instance with custom parameters if needed
            if temperature is not None or max_tokens is not None:
                custom_llm = Ollama(
                    model=self.model,
                    base_url=settings.OLLAMA_BASE_URL,
                    temperature=temperature or self.temperature,
                    num_predict=max_tokens or self.max_tokens
                )
                response = custom_llm.invoke(prompt, stop=stop)
            else:
                response = self.llm.invoke(prompt, stop=stop)
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            raise
    
    def generate_with_system(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate text with system and user prompts.
        
        Args:
            system_prompt: System instruction
            user_prompt: User query
            temperature: Override default temperature
            max_tokens: Override default max tokens
        
        Returns:
            Generated text
        """
        # Combine system and user prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        return self.generate(
            prompt=full_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def check_connection(self) -> bool:
        """
        Check if Ollama is accessible.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            test_prompt = "Hello"
            response = self.generate(test_prompt, max_tokens=10)
            logger.info("Ollama connection successful")
            return True
        except Exception as e:
            logger.error(f"Ollama connection failed: {str(e)}")
            return False


# Factory function for creating clients
def create_llm_client(
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> OllamaClient:
    """
    Factory function to create LLM client.
    
    Args:
        temperature: Optional temperature override
        max_tokens: Optional max tokens override
    
    Returns:
        OllamaClient instance
    """
    kwargs = {}
    if temperature is not None:
        kwargs['temperature'] = temperature
    if max_tokens is not None:
        kwargs['max_tokens'] = max_tokens
    
    return OllamaClient(**kwargs)