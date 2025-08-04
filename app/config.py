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
    app.config['MISTRAL_API_KEY'] = os.getenv('MISTRAL_API_KEY')
    app.config['GROQ_API_KEY'] = os.getenv('GROQ_API_KEY')
    
    # Rétrocompatibilité
    app.config['API_KEY'] = os.getenv('TOGETHER_API_KEY')
    app.config['MISTRAL_KEY'] = os.getenv('MISTRAL_API_KEY')

    # Configuration de base (SECRET_KEY conservée pour d'autres usages potentiels)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')

    # Configuration AI
    app.config['AI_MODEL_TYPE'] = os.getenv('AI_MODEL_TYPE', 'vllm_openai')
    app.config['AI_MODEL_TYPE_FOR_RESPONSE'] = os.getenv('AI_MODEL_TYPE_FOR_RESPONSE', 'vllm_openai')
    
    # Configurations spécifiques aux modèles
    # OpenAI
    app.config['OPENAI_MODEL_NAME'] = os.getenv('OPENAI_MODEL_NAME', 'o1-mini')
    
    # Together
    app.config['TOGETHER_MODEL_NAME'] = os.getenv('TOGETHER_MODEL_NAME', 'meta-llama/Llama-3.1-70B-Instruct-Turbo')
    
    # Groq
    app.config['GROQ_MODEL_NAME'] = os.getenv('GROQ_MODEL_NAME', 'moonshotai/kimi-k2-instruct')
    
    # vLLM
    app.config['VLLM_API_BASE'] = os.getenv('VLLM_API_BASE', 'http://localhost:8000/v1')
    app.config['VLLM_MODEL_NAME'] = os.getenv('VLLM_MODEL_NAME', 'microsoft/Phi-3-mini-4k-instruct')

    # Création des répertoires nécessaires
    if not os.path.exists(app.config['IMAGE_FOLDER']):
        os.makedirs(app.config['IMAGE_FOLDER'])

    if not os.path.exists(app.config['PDF_FOLDER']):
        os.makedirs(app.config['PDF_FOLDER'])

    # Validation des configurations requises (SECRET_KEY maintenant optionnel avec valeur par défaut)
    # Aucune validation critique nécessaire
    
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