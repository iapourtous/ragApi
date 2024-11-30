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
    ...     def generate_response(self, query, system=None):
    ...         return self.client.generate(query)
"""

from abc import ABC, abstractmethod

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
        self.api_key = api_key
        self.model_name = model_name
        self.system_prompt = system_prompt or "Tu es un assistant expert et pragmatique qui répond en Français."
        self.client = None  # À initialiser dans les classes dérivées
        self.initialize_client()
        """
        Initialise une nouvelle instance du modèle de langage.

        Args:
            api_key (str, optional): Clé API pour l'authentification.
            model_name (str, optional): Nom du modèle à utiliser.
            system_prompt (str, optional): Message système personnalisé.
            **kwargs: Arguments supplémentaires spécifiques au modèle.
        """
    @abstractmethod
    def initialize_client(self):
        """
        Initialise le client API spécifique au modèle.
        
        Cette méthode doit être implémentée par chaque classe dérivée pour
        configurer la connexion avec l'API du modèle de langage.
        
        Raises:
            NotImplementedError: Si la méthode n'est pas implémentée dans la classe dérivée.
        """
        pass

    @abstractmethod
    def generate_response(self, query, system=None):
        """
        Génère une réponse à partir de la requête fournie.
        
        Cette méthode doit être implémentée par chaque classe dérivée pour
        gérer la génération de réponses spécifique au modèle.

        Args:
            query (str): La requête ou le prompt pour le modèle.
            system (str, optional): Message système personnalisé pour cette requête.
                                  Si non fourni, utilise self.system_prompt.

        Returns:
            str: La réponse générée par le modèle.

        Raises:
            NotImplementedError: Si la méthode n'est pas implémentée dans la classe dérivée.
        """
        pass