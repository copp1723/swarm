import os
import requests
import logging
import time
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from utils.file_io import safe_read_json

# Load environment variables
load_dotenv(dotenv_path='../config/.env')

logger = logging.getLogger(__name__)

class OpenRouterClient:
    """Client for interacting with OpenRouter API with robust error handling."""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    API_KEY = os.environ.get('OPENROUTER_API_KEY') or os.environ.get('OPEN_ROUTER')
    
    def __init__(self):
        if not self.API_KEY:
            logger.warning("OpenRouter API key not configured")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://mcp-executive.local",
            "X-Title": "MCP Executive Interface"
        })
        
        # Load models configuration from config file
        self._load_models_config()
        
    def _load_models_config(self):
        """Load models configuration from config file"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'models.json')
        
        # Define default config
        default_config = {
            'model_mapping': {
                "auto": "anthropic/claude-3.5-sonnet",
                "deepseek/deepseek-r1": "deepseek/deepseek-r1"
            },
            'available_models': [
                {"id": "openai/gpt-4.1", "name": "GPT 4.1", "display_name": "GPT 4.1", "provider": "OpenRouter", "description": "Latest GPT-4.1 for advanced reasoning", "capabilities": ["code", "reasoning"], "pricing": "$10.00 / 1M tokens"},
                {"id": "openai/gpt-4o", "name": "GPT 4o", "display_name": "GPT 4o", "provider": "OpenRouter", "description": "Versatile model for general tasks", "capabilities": ["text", "chat"], "pricing": "$5.00 / 1M tokens"}
            ]
        }
        
        config = safe_read_json(config_path, default_value=default_config)
        self.model_mapping = config.get('model_mapping', default_config['model_mapping'])
        self.AVAILABLE_MODELS = config.get('available_models', default_config['available_models'])
        
    def call_api(self, messages: List[Dict], model_id: str, temperature: float = 0.7, max_tokens: Optional[int] = None, retries: int = 3) -> Dict:
        """Call OpenRouter API with retry logic."""
        actual_model = self.model_mapping.get(model_id, "anthropic/claude-3.5-sonnet")
        
        payload = {
            "model": actual_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 2000,
            "stream": False
        }
        
        retry_delay = 1
        for attempt in range(retries):
            try:
                response = self.session.post(
                    f"{self.BASE_URL}/chat/completions",
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    logger.error(f"OpenRouter API failed after {retries} attempts: {str(e)}")
                    raise Exception(f"OpenRouter API error: {str(e)}")
                if hasattr(e.response, 'status_code') and e.response.status_code in [429, 503]:
                    logger.warning(f"Rate limit or service error ({e.response.status_code}), retrying in {retry_delay}s")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise
        
        raise Exception("Unexpected error in API retry loop")
    
    def get_models(self) -> List[Dict]:
        """Fetch available models from OpenRouter API."""
        if not self.API_KEY:
            return self.AVAILABLE_MODELS
            
        try:
            response = self.session.get(f"{self.BASE_URL}/models", timeout=10)
            response.raise_for_status()
            api_models = response.json().get('data', [])
            
            api_model_map = {model.get('id'): model for model in api_models}
            merged_models = []
            for our_model in self.AVAILABLE_MODELS:
                api_model = api_model_map.get(our_model['id'])
                if api_model:
                    merged_model = our_model.copy()
                    merged_model['pricing'] = f"${api_model.get('pricing', {}).get('prompt', 'N/A')} / 1M tokens"
                    merged_model['provider'] = api_model.get('owned_by', our_model['provider'])
                else:
                    merged_model = our_model.copy()
                merged_models.append(merged_model)
                
            return merged_models
        except Exception as e:
            logger.error(f"Failed to fetch OpenRouter models: {str(e)}")
            return self.AVAILABLE_MODELS