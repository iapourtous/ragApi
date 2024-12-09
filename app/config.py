import os
from dotenv import load_dotenv

def setup_config(app):
    """
    Configure l'application Flask en chargeant les variables d'environnement
    depuis le fichier .env
    """
    # Configuration du modèle
    app.config['MODEL_PATH'] = os.getenv('MODEL_PATH', 'model')
    app.config['DEVICE'] = os.getenv('DEVICE', 'cpu')   
    
    # Chargement des variables d'environnement
    load_dotenv()

    # Configuration des chemins
    app.config['FOLDER_PATH'] = os.getenv('FOLDER_PATH', 'db')
    app.config['PDF_FOLDER'] = os.path.abspath(os.getenv('PDF_FOLDER', 'pdf'))
    app.config['IMAGE_FOLDER'] = os.path.abspath(os.getenv('IMAGE_FOLDER', 'images'))

    # Configuration des clés API
    app.config['API_KEY'] = os.getenv('API_KEY')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['RECAPTCHA_API_KEY'] = os.getenv('RECAPTCHA_API_KEY')
    app.config['RECAPTCHA_SITE_KEY'] = os.getenv('RECAPTCHA_SITE_KEY')
    app.config['MISTRAL_KEY'] = os.getenv('MISTRAL_KEY')

    # Configuration AI
    app.config['AI_MODEL_TYPE'] = os.getenv('AI_MODEL_TYPE', 'vllm_openai')
    app.config['AI_MODEL_TYPE_FOR_REPONSE'] = os.getenv('AI_MODEL_TYPE_FOR_REPONSE', 'hyperbolic')

    # Création des répertoires nécessaires
    if not os.path.exists(app.config['IMAGE_FOLDER']):
        os.makedirs(app.config['IMAGE_FOLDER'])

    if not os.path.exists(app.config['PDF_FOLDER']):
        os.makedirs(app.config['PDF_FOLDER'])

    # Validation des configurations requises
    required_configs = [
        'API_KEY',
        'SECRET_KEY',
        'RECAPTCHA_API_KEY',
        'RECAPTCHA_SITE_KEY',
        'MISTRAL_KEY'
    ]

    missing_configs = [config for config in required_configs if not app.config.get(config)]
    if missing_configs:
        raise ValueError(f"Configurations manquantes : {', '.join(missing_configs)}")
    
def extract_config(app):
    """
    Crée une copie des configurations nécessaires pour les threads ou processus.
    """
    return {
        "config": {key: value for key, value in app.config.items()},
        "model": getattr(app, "model", None),
        "services": getattr(app, "services", None),
        "device": app.config.get("device")
    }