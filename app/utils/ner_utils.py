"""
Module de reconnaissance d'entités nommées (NER) pour l'application RAG API.

Ce module utilise spaCy pour identifier intelligemment les entités nommées dans les textes,
remplaçant la logique simpliste de détection de mots en majuscules. Il fournit des fonctions
pour extraire les entités pertinentes (personnes, lieux, organisations, etc.) et vérifier
leur présence dans les textes de référence.
"""

import logging
import spacy
from typing import List, Dict, Set, Optional
from functools import lru_cache

# Cache global pour le modèle spaCy
_nlp_model = None

def get_spacy_model(language="fr"):
    """
    Charge et retourne le modèle spaCy pour la langue spécifiée.
    
    Args:
        language (str): Code de langue ('fr', 'en', etc.)
        
    Returns:
        spacy.Language: Modèle spaCy chargé
    """
    global _nlp_model
    
    if _nlp_model is None:
        try:
            # Essayer d'abord le modèle français
            if language == "fr":
                _nlp_model = spacy.load("fr_core_news_sm")
            else:
                # Fallback sur le modèle anglais
                _nlp_model = spacy.load("en_core_web_sm")
            logging.info(f"Modèle spaCy chargé : {_nlp_model.meta['name']}")
        except OSError as e:
            logging.warning(f"Impossible de charger le modèle spaCy {language}: {e}")
            logging.warning("Tentative de chargement du modèle anglais...")
            try:
                _nlp_model = spacy.load("en_core_web_sm")
                logging.info("Modèle anglais chargé comme fallback")
            except OSError:
                logging.error("Aucun modèle spaCy disponible. Installation requise:")
                logging.error("pip install spacy && python -m spacy download fr_core_news_sm")
                raise Exception("Modèle spaCy non disponible")
    
    return _nlp_model

@lru_cache(maxsize=1000)
def extract_named_entities(text: str, language: str = "fr") -> Dict[str, List[str]]:
    """
    Extrait les entités nommées d'un texte en utilisant spaCy.
    
    Cette fonction identifie les entités importantes comme les personnes, lieux,
    organisations, événements, et œuvres d'art. Elle utilise un cache pour éviter
    de retraiter les mêmes textes.
    
    Args:
        text (str): Texte à analyser
        language (str): Langue du texte (défaut: "fr")
        
    Returns:
        Dict[str, List[str]]: Dictionnaire avec les types d'entités et leurs valeurs
        {
            'PERSON': ['Jésus', 'Marie'],
            'GPE': ['Jérusalem'],
            'ORG': ['Église'],
            'EVENT': ['Crucifixion'],
            'WORK_OF_ART': ['Bible']
        }
    """
    try:
        nlp = get_spacy_model(language)
        doc = nlp(text)
        
        entities = {
            'PERSON': [],      # Personnes
            'GPE': [],         # Lieux géopolitiques (villes, pays)
            'LOC': [],         # Lieux géographiques
            'ORG': [],         # Organisations
            'EVENT': [],       # Événements
            'WORK_OF_ART': [], # Œuvres d'art, livres
            'MISC': []         # Divers (entités importantes non classées)
        }
        
        for ent in doc.ents:
            entity_text = ent.text.strip()
            entity_label = ent.label_
            
            # Filtrer les entités trop courtes ou non pertinentes
            if len(entity_text) < 2:
                continue
            
            # Mapper les labels spaCy vers nos catégories
            if entity_label in ['PER', 'PERSON']:
                entities['PERSON'].append(entity_text)
            elif entity_label in ['GPE', 'GEOP']:  # Entités géopolitiques
                entities['GPE'].append(entity_text)
            elif entity_label in ['LOC', 'LOCATION']:  # Lieux
                entities['LOC'].append(entity_text)
            elif entity_label in ['ORG', 'ORGANIZATION']:
                entities['ORG'].append(entity_text)
            elif entity_label in ['EVENT']:
                entities['EVENT'].append(entity_text)
            elif entity_label in ['WORK_OF_ART', 'TITLE']:
                entities['WORK_OF_ART'].append(entity_text)
            elif entity_label in ['MISC', 'MISCELLANEOUS']:
                entities['MISC'].append(entity_text)
        
        # Supprimer les doublons tout en préservant l'ordre
        for category in entities:
            entities[category] = list(dict.fromkeys(entities[category]))
        
        logging.debug(f"Entités extraites: {entities}")
        return entities
        
    except Exception as e:
        logging.error(f"Erreur lors de l'extraction des entités: {e}")
        # Fallback : retourner un dictionnaire vide
        return {
            'PERSON': [], 'GPE': [], 'LOC': [], 'ORG': [], 
            'EVENT': [], 'WORK_OF_ART': [], 'MISC': []
        }

def flatten_entities(entities_dict: Dict[str, List[str]]) -> List[str]:
    """
    Aplati le dictionnaire d'entités en une liste simple.
    
    Args:
        entities_dict (Dict[str, List[str]]): Dictionnaire d'entités par catégorie
        
    Returns:
        List[str]: Liste plate de toutes les entités
    """
    all_entities = []
    for category, entity_list in entities_dict.items():
        all_entities.extend(entity_list)
    return all_entities

def verify_entities_in_text(entities: List[str], reference_text: str, language: str = "fr") -> List[str]:
    """
    Vérifie quelles entités sont présentes dans le texte de référence.
    
    Cette fonction effectue une vérification robuste en normalisant les textes
    et en cherchant les entités même avec des variations d'accents ou de casse.
    
    Args:
        entities (List[str]): Liste des entités à vérifier
        reference_text (str): Texte de référence dans lequel chercher
        language (str): Langue du texte
        
    Returns:
        List[str]: Liste des entités trouvées dans le texte de référence
    """
    from .text_utils import normalize_text
    
    if not entities or not reference_text:
        return []
    
    # Normaliser le texte de référence pour la recherche
    normalized_reference = normalize_text(reference_text)
    reference_words = set(normalized_reference.split())
    
    found_entities = []
    
    for entity in entities:
        # Vérifier l'entité telle quelle
        normalized_entity = normalize_text(entity)
        
        # Vérifier si l'entité complète est dans le texte
        if normalized_entity in normalized_reference:
            found_entities.append(entity)
            continue
        
        # Vérifier chaque mot de l'entité (pour les entités composées)
        entity_words = normalized_entity.split()
        if len(entity_words) > 1:
            # Pour les entités composées, vérifier si tous les mots sont présents
            if all(word in reference_words for word in entity_words):
                found_entities.append(entity)
        else:
            # Pour les entités simples, vérifier si le mot est présent
            if normalized_entity in reference_words:
                found_entities.append(entity)
    
    logging.debug(f"Entités trouvées dans le texte: {found_entities}")
    return found_entities

def search_named_entities(text: str, language: str = "fr") -> List[str]:
    """
    Fonction principale pour remplacer search_upper_words().
    
    Extrait les entités nommées d'un texte et les retourne sous forme de liste simple,
    en remplacement de l'ancienne logique basée sur la capitalisation.
    
    Args:
        text (str): Texte à analyser
        language (str): Langue du texte
        
    Returns:
        List[str]: Liste des entités nommées importantes trouvées
    """
    try:
        # Extraire toutes les entités
        entities_dict = extract_named_entities(text, language)
        
        # Privilégier certains types d'entités pour les requêtes
        priority_entities = []
        
        # Ajouter les personnes en priorité (ex: Jésus, Marie, etc.)
        priority_entities.extend(entities_dict.get('PERSON', []))
        
        # Ajouter les lieux importants
        priority_entities.extend(entities_dict.get('GPE', []))
        priority_entities.extend(entities_dict.get('LOC', []))
        
        # Ajouter les organisations
        priority_entities.extend(entities_dict.get('ORG', []))
        
        # Ajouter les œuvres d'art et titres
        priority_entities.extend(entities_dict.get('WORK_OF_ART', []))
        
        # Ajouter les événements
        priority_entities.extend(entities_dict.get('EVENT', []))
        
        # Ajouter les entités diverses
        priority_entities.extend(entities_dict.get('MISC', []))
        
        # Supprimer les doublons tout en préservant l'ordre
        result = list(dict.fromkeys(priority_entities))
        
        logging.debug(f"Entités nommées extraites de '{text[:50]}...': {result}")
        return result
        
    except Exception as e:
        logging.error(f"Erreur dans search_named_entities: {e}")
        # Fallback vers l'ancienne méthode en cas d'erreur
        from .text_utils import search_upper_words
        logging.warning("Fallback vers search_upper_words")
        return search_upper_words(text)

def get_entity_keywords_for_query(query: str, language: str = "fr") -> List[str]:
    """
    Extrait les mots-clés d'entités nommées d'une requête utilisateur.
    
    Cette fonction est spécialement conçue pour traiter les requêtes utilisateur
    et extraire les entités les plus pertinentes pour la recherche.
    
    Args:
        query (str): Requête utilisateur
        language (str): Langue de la requête
        
    Returns:
        List[str]: Liste des entités nommées importantes pour la recherche
    """
    entities = search_named_entities(query, language)
    
    # Filtrer les entités trop courtes pour être significatives
    filtered_entities = [entity for entity in entities if len(entity.strip()) >= 2]
    
    logging.info(f"Mots-clés d'entités extraits de la requête: {filtered_entities}")
    return filtered_entities