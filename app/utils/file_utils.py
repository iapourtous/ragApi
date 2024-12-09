import os
import json
import logging
from .cache_utils import LRUCache
from ..models.files_book import FilesBook

# Initialisation d'un cache LRU avec une capacité de 30 éléments
memory_cache = LRUCache(capacity=30)

def load_processed_data(app, file_name):
    """
    Charge les données traitées depuis le cache en mémoire ou depuis le disque si elles ne sont pas en cache.

    :param app: Instance de l'application Flask pour accéder aux configurations.
    :param file_name: Nom du fichier sans extension .db.
    :return: Instance de FilesBook contenant les données traitées ou None en cas d'erreur.
    """
    # Tente de récupérer les données depuis le cache en mémoire
    cached_data = memory_cache.get(file_name)
    if cached_data:
        logging.info("Données récupérées depuis le cache en mémoire.")
        return cached_data

    logging.info(f"Aucune donnée en cache pour : {file_name}. Chargement depuis le fichier.")
    try:
        # Construction du chemin complet vers le fichier .db
        try:
            folder = app.config['FOLDER_PATH']  # Flask app
        except AttributeError:
            folder = app['config']['FOLDER_PATH']  # Copie de configuration
        file_path = os.path.join(folder, f"{file_name}.db")
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Création d'une instance de FilesBook à partir des données
        book = FilesBook.from_dict(data)
        
        # Ajout des données au cache en mémoire
        memory_cache.put(file_name, book)
        logging.info(f"Données chargées depuis le fichier et ajoutées au cache pour : {file_name}")
        return book
    except Exception as e:
        logging.error(f"Erreur lors du chargement des données depuis le fichier {file_name}.db : {e}")
        return None

def save_processed_data(file_name, book):
    """
    Sauvegarde les données traitées dans le cache en mémoire et sur le disque.

    :param file_name: Nom du fichier sans extension .db.
    :param book: Instance de FilesBook ou dictionnaire contenant les données à sauvegarder.
    """
    # Convertir en FilesBook si ce n'est pas déjà le cas
    if not isinstance(book, FilesBook):
        book = FilesBook.from_dict(book)

    # Ajoute ou met à jour les données dans le cache en mémoire
    memory_cache.put(file_name, book)

    try:
        # Construction du chemin complet vers le fichier .db
        file_path = f"{file_name}.db"
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(book.to_dict(), file, ensure_ascii=False, indent=4)
        logging.info(f"Données traitées sauvegardées sur le disque pour : {file_name}")
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde des données sur le disque pour {file_name}.db : {e}")

def load_partial_data(file_name):
    """
    Charge les données partielles depuis un fichier partiel pour permettre la reprise du traitement.

    :param file_name: Chemin complet vers le fichier partiel.
    :return: Instance de FilesBook contenant les données partielles ou None en cas d'erreur.
    """
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            data = json.load(file)
        book = FilesBook.from_dict(data)
        logging.info(f"Données partielles chargées depuis le fichier : {file_name}")
        return book
    except Exception as e:
        logging.error(f"Erreur lors du chargement des données partielles depuis {file_name} : {e}")
        return None

def save_partial_data(file_name, book):
    """
    Sauvegarde les données partielles dans un fichier pour permettre la reprise du traitement.

    :param file_name: Chemin complet vers le fichier partiel.
    :param book: Instance de FilesBook ou dictionnaire contenant les données à sauvegarder.
    """
    try:
        # Convertir en FilesBook si ce n'est pas déjà le cas
        if not isinstance(book, FilesBook):
            book = FilesBook.from_dict(book)

        with open(file_name, 'w', encoding='utf-8') as file:
            json.dump(book.to_dict(), file, ensure_ascii=False, indent=4)
        logging.info(f"Données partielles sauvegardées sur le disque pour : {file_name}")
    except Exception as e:
        logging.error(f"Erreur lors de la sauvegarde des données partielles sur {file_name} : {e}")

def remove_partial_data(file_name):
    """
    Supprime un fichier de données partielles après que le traitement soit terminé.

    :param file_name: Chemin complet vers le fichier partiel à supprimer.
    """
    try:
        os.remove(file_name)
        logging.info(f"Fichier de données partielles supprimé : {file_name}")
    except Exception as e:
        logging.error(f"Erreur lors de la suppression du fichier partiel {file_name} : {e}")

def ensure_directory_exists(directory_path):
    """
    S'assure que le répertoire existe, le crée si nécessaire.

    :param directory_path: Chemin du répertoire à vérifier/créer.
    """
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path)
            logging.info(f"Répertoire créé : {directory_path}")
        except Exception as e:
            logging.error(f"Erreur lors de la création du répertoire {directory_path} : {e}")
            raise

def get_file_path(app_config, file_name, file_type='db'):
    """
    Construit le chemin complet pour un fichier.

    :param app_config: Configuration de l'application Flask.
    :param file_name: Nom du fichier.
    :param file_type: Type de fichier ('db' ou 'partial').
    :return: Chemin complet du fichier.
    """
    base_path = app_config['FOLDER_PATH']
    if file_type == 'db':
        return os.path.join(base_path, f"{file_name}.db")
    elif file_type == 'partial':
        return os.path.join(base_path, f"{file_name}.partial")
    else:
        raise ValueError(f"Type de fichier non supporté : {file_type}")