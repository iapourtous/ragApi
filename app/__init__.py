"""
Module principal d'initialisation de l'application RAG API.

Ce module contient la fonction factory pour créer et configurer l'instance
de l'application Flask. Il gère l'initialisation du CORS, la configuration,
le chargement des modèles d'IA, la mise en place des routes et des services.
"""
from flask import Flask
from flask_cors import CORS
from .services.sevice_manager import ServiceManager
import logging
from .model_loader import get_model, get_device

def create_app(config=None):
    """
    Crée et configure l'application Flask.
    
    Returns:
        Flask: L'application Flask configurée
    """
    # Création de l'instance Flask
    app = Flask(__name__)


    CORS(app, resources={r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }})

    # Configuration du logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Initialisation de l'application...")

    # Configuration de l'application
    from .config import setup_config
    setup_config(app)
    logger.info("Configuration chargée")

    # Initialisation du gestionnaire de services avec la configuration
    app.services = ServiceManager(app.config)

    # Configuration des blueprints
    from .routes import init_routes
    init_routes(app)
    logger.info("Routes configurées via blueprints")

    # Chargement du modèle et configuration du device
    try:
        app.model = get_model()
        app.config['device'] = get_device()
        logger.info(f"Modèle chargé sur le device : {app.config['device']}")
    except Exception as e:
        logger.error(f"Erreur lors du chargement du modèle : {e}")
        raise

    # Plus besoin d'initialisation utilisateur
    logger.info("Application sans authentification - aucun utilisateur par défaut requis")

    logger.info("Initialisation de l'application terminée avec succès")
    return app