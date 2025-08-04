"""
Utilitaires pour la gestion des modèles d'IA.

Ce module contient des fonctions utilitaires pour manipuler les modèles d'IA,
gérer les clés API et faciliter l'interopérabilité entre différents fournisseurs.
"""
from flask import current_app

def get_api_key_for_model(model_type, config=None):
    """
    Récupère la clé API appropriée pour un type de modèle donné.
    
    Cette fonction centralise la logique d'association des modèles
    à leurs clés API respectives, évitant ainsi la duplication de code.
    
    Args:
        model_type (str): Type de modèle ('openai', 'together', 'groq', 'vllm_openai')
        config (dict, optional): Configuration contenant les clés API. Si None, utilise current_app.config
        
    Returns:
        str: Clé API correspondante au modèle ou None si non trouvée
    """
    # Utiliser le contexte Flask si config n'est pas fourni
    if config is None and current_app:
        config = current_app.config
    
    # Mapping des types de modèles vers les noms de clés d'API
    api_key_map = {
        "openai": "OPENAI_API_KEY",
        "together": "TOGETHER_API_KEY",
        "groq": "GROQ_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "vllm_openai": None  # vLLM ne nécessite pas de clé API réelle
    }
    
    # Récupérer le nom de la clé pour ce type de modèle
    key_name = api_key_map.get(model_type)
    
    # Si config est None ou key_name est None, retourner None
    if config is None or key_name is None:
        return None
        
    # Retourner la valeur de la clé API
    return config.get(key_name)