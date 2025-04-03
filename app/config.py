import os
from dotenv import load_dotenv

def setup_config(app):
    """
    Configure l'application Flask en chargeant les variables d'environnement
    depuis le fichier .env
    """
    # Chargement des variables d'environnement
    load_dotenv()
    
    # Configuration du modèle
    app.config['MODEL_PATH'] = os.getenv('MODEL_PATH', 'model')
    app.config['DEVICE'] = os.getenv('DEVICE', 'cpu')   

    # Configuration des chemins
    app.config['FOLDER_PATH'] = os.getenv('FOLDER_PATH', 'db')
    app.config['PDF_FOLDER'] = os.path.abspath(os.getenv('PDF_FOLDER', 'pdf'))
    app.config['IMAGE_FOLDER'] = os.path.abspath(os.getenv('IMAGE_FOLDER', 'images'))

    # Clés API des modèles LLM
    app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    app.config['TOGETHER_API_KEY'] = os.getenv('TOGETHER_API_KEY')
    app.config['QWEN_API_KEY'] = os.getenv('QWEN_API_KEY')
    app.config['MISTRAL_API_KEY'] = os.getenv('MISTRAL_API_KEY')
    
    # Rétrocompatibilité
    app.config['API_KEY'] = os.getenv('TOGETHER_API_KEY')
    app.config['MISTRAL_KEY'] = os.getenv('MISTRAL_API_KEY')

    # Clés API pour l'application
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['RECAPTCHA_API_KEY'] = os.getenv('RECAPTCHA_API_KEY')
    app.config['RECAPTCHA_SITE_KEY'] = os.getenv('RECAPTCHA_SITE_KEY')

    # Configuration AI
    app.config['AI_MODEL_TYPE'] = os.getenv('AI_MODEL_TYPE', 'vllm_openai')
    app.config['AI_MODEL_TYPE_FOR_REPONSE'] = os.getenv('AI_MODEL_TYPE_FOR_REPONSE', 'vllm_openai')
    
    # Configurations spécifiques aux modèles
    # OpenAI
    app.config['OPENAI_MODEL_NAME'] = os.getenv('OPENAI_MODEL_NAME', 'o1-mini')
    
    # Together
    app.config['TOGETHER_MODEL_NAME'] = os.getenv('TOGETHER_MODEL_NAME', 'Qwen/Qwen2.5-72B-Instruct-Turbo')
    
    # Qwen
    app.config['QWEN_MODEL_NAME'] = os.getenv('QWEN_MODEL_NAME', 'qwen-max')
    app.config['QWEN_API_BASE'] = os.getenv('QWEN_API_BASE', 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1')
    
    # vLLM
    app.config['VLLM_API_BASE'] = os.getenv('VLLM_API_BASE', 'http://localhost:8000/v1')
    app.config['VLLM_MODEL_NAME'] = os.getenv('VLLM_MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4')

    # Création des répertoires nécessaires
    if not os.path.exists(app.config['IMAGE_FOLDER']):
        os.makedirs(app.config['IMAGE_FOLDER'])

    if not os.path.exists(app.config['PDF_FOLDER']):
        os.makedirs(app.config['PDF_FOLDER'])

    # Validation des configurations requises
    required_configs = [
        'SECRET_KEY',
        'RECAPTCHA_API_KEY',
        'RECAPTCHA_SITE_KEY'
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