"""
Module pour le modèle OpenAI.

Ce module fournit une implémentation de BaseLLMModel pour les modèles OpenAI.
"""
from .base_model import BaseLLMModel
import openai
from typing import Dict, Any, Optional

class OpenAIModel(BaseLLMModel):
    """
    Implémentation du modèle OpenAI.
    
    Cette classe permet d'interagir avec les modèles d'OpenAI (o1-mini, GPT-4, etc.)
    en respectant l'interface commune définie dans BaseLLMModel.
    """
    
    def initialize_client(self):
        """
        Initialise le client OpenAI avec la clé API fournie.
        """
        openai.api_key = self.api_key

    def generate_response(self, 
                         query: str, 
                         system: Optional[str] = None, 
                         temperature: float = 0.7, 
                         max_tokens: int = 1000,
                         stream: bool = False,
                         **kwargs) -> Dict[str, Any]:
        """
        Génère une réponse en utilisant l'API OpenAI.
        
        Args:
            query: La requête utilisateur.
            system: Le prompt système (utilise self.system_prompt si non fourni).
            temperature: Contrôle la créativité de la réponse (0.0-1.0).
            max_tokens: Nombre maximum de tokens dans la réponse.
            stream: Si True, retourne la réponse en streaming.
            **kwargs: Arguments supplémentaires à passer à l'API OpenAI.
            
        Returns:
            Dictionnaire contenant la réponse et les métadonnées.
        """
        try:
            system_prompt = system or self.system_prompt
            model_name = self.model_name or "o1-mini"
            
            response = openai.chat.completions.create(
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
                # Implémentation du streaming à compléter si nécessaire
                return self._handle_streaming_response(response)
                
            return {
                "content": response.choices[0].message.content,
                "model": model_name,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except Exception as e:
            return self.handle_error(e)
            
    def _handle_streaming_response(self, response):
        """
        Méthode auxiliaire pour gérer les réponses en streaming.
        Cette implémentation de base collecte et renvoie le contenu complet.
        
        Args:
            response: L'objet de réponse en streaming d'OpenAI.
            
        Returns:
            Dictionnaire contenant la réponse complète.
        """
        # Implémentation simplifiée, à améliorer selon les besoins
        content = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content += chunk.choices[0].delta.content
                
        return {
            "content": content,
            "model": self.model_name,
            "usage": {
                "total_tokens": -1  # Information non disponible en streaming
            }
        }