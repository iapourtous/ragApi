"""
Module factory pour la création et la gestion des différents modèles d'IA.

Ce module fournit une interface unifiée pour instancier et utiliser différents
modèles d'IA supportés par l'application, tout en assurant une gestion cohérente
des API keys et des configurations.
"""
from .vllm_openai_model import VLLMOpenAIModel
from .together_model import TogetherModel
from .openai_model import OpenAIModel
from .groq_model import GroqModel
from flask import current_app
import logging
import importlib

# Importer model_utils dynamiquement pour éviter les dépendances circulaires
try:
    model_utils = importlib.import_module('app.utils.model_utils')
    get_api_key_for_model = model_utils.get_api_key_for_model
except ImportError:
    # Fonction de secours au cas où l'import échoue
    def get_api_key_for_model(model_type, config=None):
        if config is None and current_app:
            config = current_app.config
        
        key_map = {
            "openai": "OPENAI_API_KEY",
            "together": "TOGETHER_API_KEY",
            "groq": "GROQ_API_KEY",
            "vllm_openai": None
        }
        
        key_name = key_map.get(model_type)
        if config is None or key_name is None:
            return None
        return config.get(key_name)

class AIModel:
    """
    Classe factory pour la création et la gestion des différents modèles d'IA.
    
    Cette classe fournit une interface unifiée pour instancier et utiliser différents
    modèles d'IA (OpenAI, Together, Groq, VLLM) de manière cohérente.
    """
    @staticmethod
    def get_model(model_type, api_key=None, **kwargs):
        """
        Crée et retourne une instance du modèle d'IA spécifié.

        Args:
            model_type (str): Type de modèle à instancier ('openai', 'together', 'groq', 'vllm_openai')
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
            "together": TogetherModel,
            "groq": GroqModel,
            "vllm_openai": VLLMOpenAIModel,
        }

        # Si une instance de Flask est active, utiliser les configurations
        if current_app:
            config = current_app.config
            
            # Déterminer la clé API appropriée si non fournie explicitement
            if api_key is None:
                api_key = get_api_key_for_model(model_type, config)
                
            # Déterminer le nom du modèle approprié si non spécifié dans kwargs
            if 'model_name' not in kwargs:
                model_name_map = {
                    "openai": config.get('OPENAI_MODEL_NAME'),
                    "together": config.get('TOGETHER_MODEL_NAME'),
                    "groq": config.get('GROQ_MODEL_NAME'),
                    "vllm_openai": config.get('VLLM_MODEL_NAME')
                }
                model_name = model_name_map.get(model_type)
                if model_name:
                    kwargs['model_name'] = model_name
                    
            # Ajouter l'URL de base pour les APIs qui en ont besoin
            if model_type == "vllm_openai" and 'api_base_url' not in kwargs:
                kwargs['api_base_url'] = config.get('VLLM_API_BASE')

        if model_type in model_classes:
            try:
                return model_classes[model_type](api_key=api_key, **kwargs)
            except Exception as e:
                logging.error(f"Erreur lors de la création du modèle {model_type}: {e}")
                raise
        else:
            raise ValueError(f"Type de modèle non supporté : {model_type}")

    @staticmethod
    def generate_response(model_type, api_key, query, system=None, **kwargs):
        """
        Génère une réponse à partir d'une requête en utilisant le modèle spécifié.

        Cette méthode crée une instance temporaire du modèle spécifié et l'utilise
        pour générer une réponse à la requête fournie.

        Args:
            model_type (str): Type de modèle à utiliser ('openai', 'together', 'groq', 'vllm_openai')
            api_key (str): Clé API pour l'authentification au service
            query (str): Requête ou prompt pour le modèle
            system (str, optional): Message système pour contextualiser la requête
            **kwargs: Arguments additionnels spécifiques au modèle

        Returns:
            str ou dict: Réponse générée par le modèle (contenu textuel ou dictionnaire complet)

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
        return_full_response = kwargs.pop('return_full_response', False)
        
        # Si la clé API est None, essayer de la récupérer
        if api_key is None and current_app:
            api_key = get_api_key_for_model(model_type, current_app.config)
            
        model = AIModel.get_model(model_type, api_key, **kwargs)
        
        try:
            response = model.generate_response(query, system=system, **kwargs)
            
            # Retourner soit le contenu textuel uniquement, soit la réponse complète
            if return_full_response:
                return response
            else:
                return response.get('content', '') if isinstance(response, dict) else response
        except Exception as e:
            logging.error(f"Erreur lors de la génération de réponse avec {model_type}: {e}")
            if return_full_response:
                return {"content": f"Erreur: {str(e)}", "error": True}
            else:
                return f"Erreur: {str(e)}"