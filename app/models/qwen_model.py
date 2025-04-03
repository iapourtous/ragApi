"""
Module pour le modèle Qwen via DashScope API.

Ce module fournit une implémentation de BaseLLMModel pour les modèles Qwen
via l'API DashScope compatible avec OpenAI.
"""
from .base_model import BaseLLMModel
import openai
from openai import OpenAI
from typing import Dict, Any, Optional
import logging

class QwenModel(BaseLLMModel):
    """
    Implémentation du modèle Qwen.
    
    Cette classe permet d'interagir avec les modèles Qwen via l'API DashScope
    d'Alibaba Cloud en respectant l'interface commune définie dans BaseLLMModel.
    """
    
    def initialize_client(self):
        """
        Initialise le client OpenAI compatible avec l'API DashScope.
        """
        api_base = getattr(self, "api_base", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=api_base
        )

    def generate_response(self, 
                         query: str, 
                         system: Optional[str] = None, 
                         temperature: float = 0.2, 
                         max_tokens: int = 8192,
                         stream: bool = False,
                         **kwargs) -> Dict[str, Any]:
        """
        Génère une réponse en utilisant l'API Qwen (DashScope).
        
        Args:
            query: La requête utilisateur.
            system: Le prompt système (utilise self.system_prompt si non fourni).
            temperature: Contrôle la créativité de la réponse (0.0-1.0).
            max_tokens: Nombre maximum de tokens dans la réponse.
            stream: Si True, retourne la réponse en streaming.
            **kwargs: Arguments supplémentaires à passer à l'API Qwen.
            
        Returns:
            Dictionnaire contenant la réponse et les métadonnées.
        """
        try:
            system_prompt = system or self.system_prompt
            model_name = self.model_name or "qwen-max"
            
            max_retries = kwargs.pop("max_retries", 3)
            
            # Gérer les tentatives multiples en cas d'erreur
            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": query},
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=stream,
                        **kwargs
                    )
                    
                    if stream:
                        return self._handle_streaming_response(response)
                    
                    # Formatage standardisé de la réponse
                    return {
                        "content": response.choices[0].message.content.strip(),
                        "model": model_name,
                        "usage": {
                            "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                            "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                            "total_tokens": getattr(response.usage, "total_tokens", 0)
                        }
                    }
                    
                except Exception as e:
                    logging.warning(f"Tentative {attempt+1}/{max_retries} échouée: {str(e)}")
                    if attempt == max_retries - 1:
                        raise  # Relancer l'exception si dernière tentative
            
        except Exception as e:
            return self.handle_error(e)
            
    def _handle_streaming_response(self, response):
        """
        Méthode auxiliaire pour gérer les réponses en streaming.
        
        Args:
            response: L'objet de réponse en streaming.
            
        Returns:
            Dictionnaire contenant la réponse complète.
        """
        content = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content
                
        return {
            "content": content.strip(),
            "model": self.model_name,
            "usage": {
                "total_tokens": -1  # Information non disponible en streaming
            }
        }