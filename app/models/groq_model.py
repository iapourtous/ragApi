"""
Module pour le modèle Groq.

Ce module fournit une implémentation de BaseLLMModel pour les modèles Groq,
incluant le support du modèle Moonshot AI Kimi-K2-Instruct.
"""
from .base_model import BaseLLMModel
from groq import Groq
from typing import Dict, Any, Optional
import logging

class GroqModel(BaseLLMModel):
    """
    Implémentation du modèle Groq.
    
    Cette classe permet d'interagir avec les modèles disponibles sur Groq,
    incluant le modèle Moonshot AI Kimi-K2-Instruct, en respectant l'interface
    commune définie dans BaseLLMModel.
    """
    
    def initialize_client(self):
        """
        Initialise le client Groq avec la clé API fournie.
        """
        if not self.api_key:
            raise ValueError("Clé API Groq requise")
        self.client = Groq(api_key=self.api_key)

    def generate_response(self, 
                         query: str, 
                         system: Optional[str] = None, 
                         temperature: float = 0.1, 
                         max_tokens: int = 16384,
                         stream: bool = False,
                         **kwargs) -> Dict[str, Any]:
        """
        Génère une réponse en utilisant l'API Groq.
        
        Args:
            query: La requête utilisateur.
            system: Le prompt système (utilise self.system_prompt si non fourni).
            temperature: Contrôle la créativité de la réponse (0.0-2.0).
            max_tokens: Nombre maximum de tokens dans la réponse.
            stream: Si True, retourne la réponse en streaming.
            **kwargs: Arguments supplémentaires à passer à l'API Groq.
            
        Returns:
            Dictionnaire contenant la réponse et les métadonnées.
        """
        try:
            system_prompt = system or self.system_prompt
            model_name = self.model_name or "moonshotai/kimi-k2-instruct"
            
            # Validation des paramètres Groq
            temperature = max(0.0, min(2.0, temperature))  # Groq accepte 0.0-2.0
            max_tokens = min(max_tokens, 16384)  # Limite maximale de Groq
            
            # Paramètres par défaut pour Groq
            top_p = kwargs.pop("top_p", 1.0)
            
            # Construire les messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": query})
            
            # Filtrer les paramètres non supportés par Groq
            supported_params = ['temperature', 'max_tokens', 'top_p', 'stream', 'response_format', 'seed', 'stop', 'tools', 'tool_choice', 'user']
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in supported_params}
            
            # Paramètres de la requête
            request_params = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p,
                "stream": stream,
                **filtered_kwargs
            }
            
            logging.debug(f"Groq API request: {model_name}, temperature: {temperature}, max_tokens: {max_tokens}")
            
            response = self.client.chat.completions.create(**request_params)
            
            if stream:
                return self._handle_streaming_response(response)
                
            # Traitement de la réponse standard
            if not response.choices:
                return self.handle_error("Aucune réponse générée par le modèle Groq")
                
            content = response.choices[0].message.content
            if not content:
                return self.handle_error("Contenu vide dans la réponse Groq")
            
            return {
                "content": content.strip(),
                "model": model_name,
                "usage": {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                    "total_tokens": getattr(response.usage, "total_tokens", 0)
                },
                "finish_reason": response.choices[0].finish_reason
            }
            
        except Exception as e:
            logging.error(f"Erreur Groq API: {str(e)}")
            return self.handle_error(e)
            
    def _handle_streaming_response(self, response):
        """
        Méthode auxiliaire pour gérer les réponses en streaming.
        
        Args:
            response: L'objet de réponse en streaming de Groq.
            
        Returns:
            Dictionnaire contenant la réponse complète.
        """
        content = ""
        total_tokens = 0
        finish_reason = None
        
        try:
            for chunk in response:
                if chunk.choices:
                    choice = chunk.choices[0]
                    if choice.delta and choice.delta.content:
                        content += choice.delta.content
                    if choice.finish_reason:
                        finish_reason = choice.finish_reason
                
                # Accumulation des tokens si disponible
                if hasattr(chunk, 'usage') and chunk.usage:
                    total_tokens = chunk.usage.total_tokens
                        
        except Exception as e:
            logging.error(f"Erreur lors du streaming Groq: {str(e)}")
            return self.handle_error(e)
                
        return {
            "content": content.strip(),
            "model": self.model_name or "moonshotai/kimi-k2-instruct",
            "usage": {
                "total_tokens": total_tokens,
                "prompt_tokens": -1,  # Non disponible en streaming
                "completion_tokens": -1  # Non disponible en streaming
            },
            "finish_reason": finish_reason
        }
    
    def get_available_models(self):
        """
        Récupère la liste des modèles disponibles sur Groq.
        
        Returns:
            Liste des modèles disponibles ou None en cas d'erreur.
        """
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des modèles Groq: {str(e)}")
            return None
    
    @staticmethod
    def get_recommended_models():
        """
        Retourne la liste des modèles recommandés pour différents cas d'usage.
        
        Returns:
            Dictionnaire avec les modèles recommandés par catégorie.
        """
        return {
            "moonshot": "moonshotai/kimi-k2-instruct",  # Modèle principal demandé
            "fast": "llama-3.3-70b-versatile",       # Modèle rapide
            "vision": "llama-3.2-90b-vision-preview", # Modèle avec capacités vision
            "small": "llama-3.2-3b-preview",         # Modèle léger
            "code": "llama-3.3-70b-versatile"        # Bon pour le code
        }