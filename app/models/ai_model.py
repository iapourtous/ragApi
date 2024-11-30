from .vllm_openai_model import VLLMOpenAIModel
from .together_model import TogetherModel
from .hyperbolic_model import HyperbolicModel
from .openai_model import  OpenAIModel

class AIModel:
    """
    Classe factory pour la création et la gestion des différents modèles d'IA.
    
    Cette classe fournit une interface unifiée pour instancier et utiliser différents
    modèles d'IA (OpenAI, Hyperbolic, Together, VLLM) de manière cohérente.
    """
    @staticmethod
    def get_model(model_type, api_key=None, **kwargs):
        """
        Crée et retourne une instance du modèle d'IA spécifié.

        Args:
            model_type (str): Type de modèle à instancier ('openai', 'hyperbolic', 'together', 'vllm_openai')
            api_key (str, optional): Clé API pour l'authentification au service
            **kwargs: Arguments additionnels spécifiques au modèle

        Returns:
            BaseLLMModel: Instance du modèle d'IA correspondant au type spécifié

        Raises:
            ValueError: Si le type de modèle n'est pas supporté

        Examples:
            >>> model = AIModel.get_model('openai', api_key='your-api-key')
            >>> response = model.generate_response("Quelle est la capitale de la France?")
        """
        model_classes = {
            "openai": OpenAIModel,
            "hyperbolic": HyperbolicModel,
            "together": TogetherModel,
            "vllm_openai": VLLMOpenAIModel,
        }

        if model_type in model_classes:
            return model_classes[model_type](api_key=api_key, **kwargs)
        else:
            raise ValueError(f"Type de modèle non supporté : {model_type}")

    @staticmethod
    def generate_response(model_type, api_key, query, system=None, **kwargs):
        """
        Génère une réponse à partir d'une requête en utilisant le modèle spécifié.

        Cette méthode crée une instance temporaire du modèle spécifié et l'utilise
        pour générer une réponse à la requête fournie.

        Args:
            model_type (str): Type de modèle à utiliser ('openai', 'hyperbolic', 'together', 'vllm_openai')
            api_key (str): Clé API pour l'authentification au service
            query (str): Requête ou prompt pour le modèle
            system (str, optional): Message système pour contextualiser la requête
            **kwargs: Arguments additionnels spécifiques au modèle

        Returns:
            str: Réponse générée par le modèle

        Raises:
            ValueError: Si le type de modèle n'est pas supporté ou si la clé API est manquante
            Exception: Si une erreur survient lors de la génération de la réponse

        Examples:
            >>> response = AIModel.generate_response(
            ...     'openai',
            ...     'your-api-key',
            ...     "Quelle est la capitale de la France?",
            ...     system="Tu es un expert en géographie."
            ... )
            >>> print(response)
        """
        model = AIModel.get_model(model_type, api_key, **kwargs)
        return model.generate_response(query, system=system)