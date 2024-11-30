from .services.sevice_manager import ServiceManager
from flask import Flask
import logging
from .model_loader import get_model, get_device
from .services.user_service import UserService

def create_app():
    """
    Crée et configure l'application Flask.
    
    Returns:
        Flask: L'application Flask configurée
    """
    # Création de l'instance Flask
    app = Flask(__name__)

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


    # Configuration des routes
    from .routes import setup_routes
    setup_routes(app)
    logger.info("Routes configurées")

    # Chargement du modèle et configuration du device
    try:
        app.model = get_model()
        app.config['device'] = get_device()
        logger.info(f"Modèle chargé sur le device : {app.config['device']}")
    except Exception as e:
        logger.error(f"Erreur lors du chargement du modèle : {e}")
        raise

    # Initialisation de l'utilisateur par défaut
    try:
        with app.app_context():
            #user_service = UserService()
            #user_service.create_default_user()
            logger.info("Vérification/création de l'utilisateur par défaut effectuée")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de l'utilisateur par défaut : {e}")
        raise

    logger.info("Initialisation de l'application terminée avec succès")
    return app