"""
Module d'intégration du modèle vLLM avec interface compatible OpenAI.

Ce module fournit une implémentation du modèle de base BaseLLMModel pour
utiliser une instance vLLM locale (ou distante) via l'API compatible OpenAI.
Il permet d'envoyer des requêtes à un serveur vLLM et de générer des réponses
en utilisant les modèles chargés sur ce serveur.
"""
from .base_model import BaseLLMModel
import openai
from openai import OpenAI
from typing import Dict, Any, Optional
import logging

class VLLMOpenAIModel(BaseLLMModel):
    """
    Implémentation pour les modèles vLLM locaux avec interface OpenAI.
    
    Cette classe permet d'interagir avec des modèles open source
    exécutés localement via vLLM mais exposés avec une API compatible OpenAI.
    """
    
    def initialize_client(self, **kwargs):
        """
        Initialise le client OpenAI pointant vers un serveur vLLM.
        """
        # Récupère la configuration depuis les attributs ou utilise des valeurs par défaut
        api_key = self.api_key or "EMPTY"
        base_url = getattr(self, "api_base_url", "http://localhost:8000/v1")
        
        logging.info(f"Initialisation du client vLLM OpenAI avec base_url: {base_url}")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    def generate_response(self, 
                         query: str, 
                         system: Optional[str] = None, 
                         temperature: float = 0.3, 
                         max_tokens: int = 4096,
                         stream: bool = False,
                         **kwargs) -> Dict[str, Any]:
        """
        Génère une réponse en utilisant le modèle vLLM local.
        
        Args:
            query: La requête utilisateur.
            system: Le prompt système (utilise self.system_prompt si non fourni).
            temperature: Contrôle la créativité de la réponse (0.0-1.0).
            max_tokens: Nombre maximum de tokens dans la réponse.
            stream: Si True, retourne la réponse en streaming.
            **kwargs: Arguments supplémentaires à passer à l'API.
            
        Returns:
            Dictionnaire contenant la réponse et les métadonnées.
        """
        try:
            system_prompt = system or self.system_prompt
            model_name = self.model_name or "microsoft/Phi-3-mini-4k-instruct"
            
            # Paramètres par défaut de vLLM
            top_p = kwargs.pop("top_p", 0.3)
            repetition_penalty = kwargs.pop("repetition_penalty", 1.0)
            
            # Configuration spécifique à vLLM
            extra_params = {
                "repetition_penalty": repetition_penalty,
            }
            
            # Ajout des paramètres supplémentaires fournis
            for k, v in kwargs.items():
                if k.startswith("vllm_"):
                    extra_params[k[5:]] = v
            
            # Appel à l'API vLLM
            chat_response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=stream,
                extra_body=extra_params,
            )
            
            if stream:
                return self._handle_streaming_response(chat_response)
            
            # Formatage standardisé de la réponse
            try:
                usage_info = {
                    "prompt_tokens": getattr(chat_response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(chat_response.usage, "completion_tokens", 0),
                    "total_tokens": getattr(chat_response.usage, "total_tokens", 0)
                }
            except (AttributeError, TypeError):
                # Certaines implémentations de vLLM ne retournent pas d'informations d'usage
                usage_info = {"total_tokens": -1}
            
            return {
                "content": chat_response.choices[0].message.content.strip(),
                "model": model_name,
                "usage": usage_info,
                "metadata": {
                    "vllm_params": extra_params
                }
            }
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