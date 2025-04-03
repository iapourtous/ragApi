"""
Module pour le modèle Together.ai.

Ce module fournit une implémentation de BaseLLMModel pour les modèles Together.ai.
"""
from .base_model import BaseLLMModel
from together import Together
from typing import Dict, Any, Optional
import logging

class TogetherModel(BaseLLMModel):
    """
    Implémentation du modèle Together.ai.
    
    Cette classe permet d'interagir avec les modèles de Together.ai
    en respectant l'interface commune définie dans BaseLLMModel.
    """
    
    def initialize_client(self):
        """
        Initialise le client Together.ai avec la clé API fournie.
        """
        self.client = Together(api_key=self.api_key)

    def generate_response(self, 
                         query: str, 
                         system: Optional[str] = None, 
                         temperature: float = 0.1, 
                         max_tokens: int = 8192,
                         stream: bool = False,
                         **kwargs) -> Dict[str, Any]:
        """
        Génère une réponse en utilisant l'API Together.ai.
        
        Args:
            query: La requête utilisateur.
            system: Le prompt système (utilise self.system_prompt si non fourni).
            temperature: Contrôle la créativité de la réponse (0.0-1.0).
            max_tokens: Nombre maximum de tokens dans la réponse.
            stream: Si True, retourne la réponse en streaming.
            **kwargs: Arguments supplémentaires à passer à l'API Together.
            
        Returns:
            Dictionnaire contenant la réponse et les métadonnées.
        """
        try:
            system_prompt = system or self.system_prompt
            model_name = self.model_name or "Qwen/Qwen2.5-72B-Instruct-Turbo"
            
            # Paramètres par défaut
            top_p = kwargs.pop("top_p", 0.7)
            top_k = kwargs.pop("top_k", 50)
            repetition_penalty = kwargs.pop("repetition_penalty", 1.0)
            stop = kwargs.pop("stop", ["<|im_end|>"])
            
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=repetition_penalty,
                stop=stop,
                stream=stream,
                **kwargs
            )
            
            if stream:
                return self._handle_streaming_response(response)
                
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
            return self.handle_error(e)
            
    def _handle_streaming_response(self, response):
        """
        Méthode auxiliaire pour gérer les réponses en streaming.
        
        Args:
            response: L'objet de réponse en streaming de Together.
            
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