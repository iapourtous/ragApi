import torch
from sentence_transformers import SentenceTransformer
import logging
import os
from dotenv import load_dotenv
from pathlib import Path

# Chargement des variables d'environnement
load_dotenv()

# Configuration par défaut
MODEL_PATH = os.getenv('MODEL_PATH', 'model')
DEVICE = os.getenv('DEVICE', 'cpu') if os.getenv('DEVICE') else "cuda" if torch.cuda.is_available() else "cpu"
EXPORTED_MODEL_PATH = os.path.join(MODEL_PATH, "openvino_model")

# Initialisation du modèle
model = None

def model_is_exported():
    """
    Vérifie si le modèle a déjà été exporté en format OpenVINO.
    """
    return os.path.exists(EXPORTED_MODEL_PATH) and os.path.isdir(EXPORTED_MODEL_PATH)

def export_model():
    """
    Exporte le modèle au format OpenVINO.
    """
    logging.info("Exportation du modèle au format OpenVINO...")
    temp_model = SentenceTransformer("intfloat/multilingual-e5-large", backend="openvino", device=DEVICE)
    os.makedirs(EXPORTED_MODEL_PATH, exist_ok=True)
    temp_model.save_pretrained(EXPORTED_MODEL_PATH)
    logging.info(f"Modèle exporté avec succès dans {EXPORTED_MODEL_PATH}")

def initialize_model():
    """
    Initialise le modèle avec les paramètres configurés.
    Cette fonction doit être appelée une seule fois au démarrage de l'application.
    """
    global model
    try:
        if not model_is_exported():
            logging.info("Modèle OpenVINO non trouvé, exportation en cours...")
            export_model()
        
        logging.info(f"Chargement du modèle depuis {EXPORTED_MODEL_PATH} sur {DEVICE}")
        model = SentenceTransformer(EXPORTED_MODEL_PATH, device=DEVICE)  
        logging.info("Modèle chargé avec succès")
    except Exception as e:
        logging.error(f"Erreur lors du chargement du modèle : {e}")
        raise

def get_model():
    """
    Retourne l'instance du modèle.
    
    Returns:
        SentenceTransformer: Instance du modèle chargé
        
    Raises:
        RuntimeError: Si le modèle n'a pas été initialisé
    """
    if model is None:
        initialize_model()
    return model

def get_device():
    """
    Retourne le device configuré pour le modèle.
    
    Returns:
        str: 'cuda' si disponible et configuré, sinon 'cpu'
    """
    return DEVICE
