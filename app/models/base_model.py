"""
Module de base pour les modèles de langage (LLM).

Ce module définit une classe abstraite de base pour l'interaction avec différents modèles
de langage. Il fournit une interface commune que toutes les implémentations spécifiques
de modèles doivent suivre.

Classes:
    BaseLLMModel: Classe abstraite de base pour les modèles de langage.

Example:
    Pour créer un nouveau modèle de langage, héritez de BaseLLMModel:

    >>> class CustomLLMModel(BaseLLMModel):
    ...     def initialize_client(self):
    ...         self.client = CustomClient(self.api_key)
    ...     
    ...     def generate_response(self, query, system=None, temperature=0.7, max_tokens=1000):
    ...         response = self.client.generate(query, temperature=temperature)
    ...         return {
    ...             "content": response.text,
    ...             "model": self.model_name,
    ...             "usage": {"total_tokens": response.usage}
    ...         }
"""

from abc import ABC, abstractmethod
import logging
from typing import Dict, Any, Optional, Union, List

class BaseLLMModel(ABC):
    """
    Classe abstraite de base pour les modèles de langage.
    
    Cette classe définit l'interface commune que tous les modèles de langage
    doivent implémenter. Elle gère la configuration de base et force
    l'implémentation des méthodes essentielles.

    Attributes:
        api_key (str): Clé API pour l'authentification avec le service.
        model_name (str): Nom du modèle à utiliser.
        system_prompt (str): Message système par défaut pour le modèle.
        client: Client API spécifique au modèle (initialisé dans les classes dérivées).

    Args:
        api_key (str, optional): Clé API pour l'authentification.
        model_name (str, optional): Nom du modèle à utiliser.
        system_prompt (str, optional): Message système personnalisé.
        **kwargs: Arguments supplémentaires spécifiques au modèle.
    """    

    def __init__(self, api_key=None, model_name=None, system_prompt=None, **kwargs):
        """
        Initialise une nouvelle instance du modèle de langage.

        Args:
            api_key (str, optional): Clé API pour l'authentification.
            model_name (str, optional): Nom du modèle à utiliser.
            system_prompt (str, optional): Message système personnalisé.
            **kwargs: Arguments supplémentaires spécifiques au modèle.
        """
        self.api_key = api_key
        self.model_name = model_name
        self.system_prompt = system_prompt or "Tu es un assistant expert et pragmatique qui répond en Français."
        self.client = None  # À initialiser dans les classes dérivées
        self.initialize_client()
        
    @abstractmethod
    def initialize_client(self):
        """
        Initialise le client API spécifique au modèle.
        
        Cette méthode doit être implémentée par chaque classe dérivée pour
        configurer la connexion avec l'API du modèle de langage.
        
        Raises:
            Exception: Si l'initialisation échoue.
        """
        pass

    @abstractmethod
    def generate_response(self, 
                         query: str, 
                         system: Optional[str] = None, 
                         temperature: float = 0.7, 
                         max_tokens: int = 1000,
                         stream: bool = False,
                         **kwargs) -> Dict[str, Any]:
        """
        Génère une réponse à partir de la requête fournie.
        
        Cette méthode doit être implémentée par chaque classe dérivée pour
        gérer la génération de réponses spécifique au modèle.

        Args:
            query (str): La requête ou le prompt pour le modèle.
            system (str, optional): Message système personnalisé pour cette requête.
                                  Si non fourni, utilise self.system_prompt.
            temperature (float, optional): Contrôle la créativité de la réponse (0.0-1.0).
            max_tokens (int, optional): Nombre maximum de tokens dans la réponse.
            stream (bool, optional): Si True, retourne la réponse en streaming.
            **kwargs: Arguments supplémentaires spécifiques au modèle.

        Returns:
            Dict[str, Any]: Dictionnaire contenant au moins:
                - 'content': Le texte de la réponse
                - 'model': Le nom du modèle utilisé
                - 'usage': Informations sur l'utilisation (tokens)

        Raises:
            Exception: Si une erreur survient lors de la génération.
        """
        pass

    def process_image(self, 
                     image_path: str, 
                     query: str, 
                     system: Optional[str] = None,
                     temperature: float = 0.7, 
                     max_tokens: int = 1000,
                     **kwargs) -> Dict[str, Any]:
        """
        Génère une réponse à partir d'une image et d'une requête.
        
        Par défaut, cette méthode lève une exception NotImplementedError.
        Les modèles prenant en charge la vision doivent la surcharger.

        Args:
            image_path (str): Chemin vers l'image à analyser.
            query (str): La requête ou le prompt pour le modèle.
            system (str, optional): Message système personnalisé pour cette requête.
            temperature (float, optional): Contrôle la créativité de la réponse.
            max_tokens (int, optional): Nombre maximum de tokens dans la réponse.
            **kwargs: Arguments supplémentaires spécifiques au modèle.

        Returns:
            Dict[str, Any]: Dictionnaire contenant la réponse.
            
        Raises:
            NotImplementedError: Ce modèle ne supporte pas le traitement d'images.
        """
        raise NotImplementedError("Ce modèle ne supporte pas le traitement d'images.")

    def handle_error(self, exception: Exception) -> Dict[str, Any]:
        """
        Gère les erreurs survenues lors de l'interaction avec le modèle.
        
        Args:
            exception (Exception): L'exception qui s'est produite.
            
        Returns:
            Dict[str, Any]: Un dictionnaire formaté avec les informations d'erreur.
        """
        error_message = str(exception)
        logging.error(f"Erreur lors de l'interaction avec le modèle {self.model_name}: {error_message}")
        
        return {
            "content": f"Une erreur s'est produite: {error_message}",
            "model": self.model_name,
            "error": True,
            "error_type": type(exception).__name__
        }