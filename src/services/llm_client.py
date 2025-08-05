"""
Unified LLM client supporting both OpenAI and Google Gemini
"""

import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from src.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract base class for LLM clients"""
    
    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: str = None) -> str:
        """Generate text response from prompt"""
        pass
    
    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM service is available"""
        pass


class OpenAIClient(LLMClient):
    """OpenAI client implementation"""
    
    def __init__(self):
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self._available = bool(settings.OPENAI_API_KEY)
        except ImportError:
            logger.warning("OpenAI package not available")
            self.client = None
            self._available = False
    
    def generate_text(self, prompt: str, system_prompt: str = None) -> str:
        """Generate text using OpenAI GPT"""
        if not self.is_available():
            raise Exception("OpenAI client not available")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=settings.LLM_MODEL if "gpt" in settings.LLM_MODEL else "gpt-3.5-turbo",
            messages=messages,
            max_tokens=settings.MAX_TOKENS,
            temperature=settings.TEMPERATURE
        )
        
        return response.choices[0].message.content.strip()
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI"""
        if not self.is_available():
            raise Exception("OpenAI client not available")
        
        response = self.client.embeddings.create(
            model=settings.EMBEDDING_MODEL if "text-embedding" in settings.EMBEDDING_MODEL else "text-embedding-ada-002",
            input=texts
        )
        
        return [data.embedding for data in response.data]
    
    def is_available(self) -> bool:
        """Check if OpenAI is available"""
        if not self._available or not self.client:
            return False
        
        try:
            # Test with a simple call
            self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=["test"]
            )
            return True
        except Exception as e:
            logger.warning(f"OpenAI not available: {str(e)}")
            return False


class GeminiClient(LLMClient):
    """Google Gemini client implementation"""
    
    def __init__(self):
        try:
            import google.generativeai as genai
            self.genai = genai
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._available = True
            else:
                self._available = False
        except ImportError:
            logger.warning("Google Generative AI package not available")
            self.genai = None
            self._available = False
    
    def generate_text(self, prompt: str, system_prompt: str = None) -> str:
        """Generate text using Google Gemini"""
        if not self.is_available():
            raise Exception("Gemini client not available")
        
        # Combine system prompt and user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        model = self.genai.GenerativeModel(
            model_name=settings.LLM_MODEL if "gemini" in settings.LLM_MODEL else "gemini-1.5-flash"
        )
        
        generation_config = self.genai.types.GenerationConfig(
            max_output_tokens=settings.MAX_TOKENS,
            temperature=settings.TEMPERATURE,
        )
        
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        
        return response.text.strip()
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Google Gemini"""
        if not self.is_available():
            raise Exception("Gemini client not available")
        
        embeddings = []
        embedding_model = settings.EMBEDDING_MODEL if "text-embedding" in settings.EMBEDDING_MODEL else "models/text-embedding-004"
        
        for text in texts:
            result = self.genai.embed_content(
                model=embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(result['embedding'])
        
        return embeddings
    
    def is_available(self) -> bool:
        """Check if Gemini is available"""
        if not self._available or not self.genai:
            return False
        
        try:
            # Test with a simple call
            result = self.genai.embed_content(
                model="models/text-embedding-004",
                content="test",
                task_type="retrieval_document"
            )
            return True
        except Exception as e:
            logger.warning(f"Gemini not available: {str(e)}")
            return False


class LLMClientFactory:
    """Factory for creating LLM clients"""
    
    @staticmethod
    def create_client() -> LLMClient:
        """Create the appropriate LLM client based on configuration"""
        
        # Try to create clients in order of preference
        if settings.LLM_PROVIDER.lower() == "gemini":
            # Try Gemini first
            gemini_client = GeminiClient()
            if gemini_client.is_available():
                logger.info("✅ Using Google Gemini LLM")
                return gemini_client
            
            # Fallback to OpenAI
            openai_client = OpenAIClient()
            if openai_client.is_available():
                logger.info("🔄 Gemini unavailable, falling back to OpenAI")
                return openai_client
        
        else:  # OpenAI preferred
            # Try OpenAI first
            openai_client = OpenAIClient()
            if openai_client.is_available():
                logger.info("✅ Using OpenAI LLM")
                return openai_client
            
            # Fallback to Gemini
            gemini_client = GeminiClient()
            if gemini_client.is_available():
                logger.info("🔄 OpenAI unavailable, falling back to Gemini")
                return gemini_client
        
        # If neither is available, return a mock client
        logger.warning("⚠️ No LLM providers available, using fallback")
        return MockLLMClient()


class MockLLMClient(LLMClient):
    """Mock LLM client for when no real providers are available"""
    
    def generate_text(self, prompt: str, system_prompt: str = None) -> str:
        """Generate mock text response"""
        return "Mock response: Unable to process request due to LLM service unavailability."
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings"""
        import random
        import hashlib
        
        embeddings = []
        for text in texts:
            # Generate consistent mock embedding based on text hash
            text_hash = hashlib.md5(text.encode()).hexdigest()
            seed = int(text_hash[:8], 16)
            random.seed(seed)
            embedding = [random.uniform(-1, 1) for _ in range(1536)]
            embeddings.append(embedding)
        
        return embeddings
    
    def is_available(self) -> bool:
        """Mock client is always 'available' as fallback"""
        return True
