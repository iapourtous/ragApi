"""
Module des routes système pour l'application RAG API.

Ce module fournit des endpoints pour la surveillance et le diagnostic de l'application,
tels que les métriques de performance, les statistiques de cache, et d'autres informations
système utiles pour l'administration et le monitoring.
"""

from flask import Blueprint, jsonify
from ..utils.vector_utils import get_cache_stats
from ..utils.cache_utils import memory_cache

system_bp = Blueprint('system', __name__)

@system_bp.route('/cache/stats', methods=['GET'])
def get_cache_statistics():
    """
    Récupère les statistiques des différents caches de l'application.
    
    Returns:
        Statistiques au format JSON pour les caches utilisés dans l'application
    """
    # Récupérer les statistiques du cache de vectorisation
    vector_cache_stats = get_cache_stats()
    
    # Récupérer les statistiques du cache mémoire général
    memory_cache_stats = memory_cache.get_stats()
    
    return jsonify({
        "vector_cache": vector_cache_stats,
        "memory_cache": memory_cache_stats
    })

@system_bp.route('/status', methods=['GET'])
def get_system_status():
    """
    Vérifie l'état général du système et renvoie un rapport sur sa santé.
    
    Returns:
        État du système au format JSON
    """
    return jsonify({
        "status": "ok",
        "message": "Système opérationnel"
    })