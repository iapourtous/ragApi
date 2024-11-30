import torch
from sentence_transformers import SentenceTransformer
import logging
import os
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Configuration par défaut
MODEL_PATH = os.getenv('MODEL_PATH', 'model')
DEVICE = os.getenv('DEVICE', 'cpu') if os.getenv('DEVICE') else "cuda" if torch.cuda.is_available() else "cpu"

# Initialisation du modèle
model = None

def initialize_model():
    """
    Initialise le modèle avec les paramètres configurés.
    Cette fonction doit être appelée une seule fois au démarrage de l'application.
    """
    global model
    try:
        logging.info(f"Chargement du modèle depuis {MODEL_PATH} sur {DEVICE}")
        model = SentenceTransformer(MODEL_PATH, device=DEVICE)
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
