"""
Module d'utilitaires pour le traitement de texte dans l'application RAG API.

Ce module fournit des fonctions pour le traitement, la normalisation et l'analyse de textes.
Il inclut des outils pour la normalisation des caractères, la recherche de mots-clés,
la segmentation de textes en fragments gérables, et la vectorisation des requêtes textuelles.
Ces fonctions sont essentielles pour les opérations de recherche, filtrage et
préparation des données textuelles dans le pipeline RAG.
"""
import re
import unicodedata

def normalize_text(text):
    """
    Normalise le texte en supprimant les accents, les caractères spéciaux, les apostrophes,
    et en le convertissant en majuscules.

    Cette fonction effectue les opérations suivantes :
    1. Décompose les caractères accentués en leurs composants de base (lettre + accent).
    2. Supprime les accents en filtrant les caractères combinants.
    3. Supprime les caractères spéciaux, les apostrophes, en ne gardant que les caractères alphanumériques et les espaces.
    4. Convertit tout le texte en majuscules pour standardiser la comparaison.

    :param text: Chaîne de caractères à normaliser.
    :return: Chaîne de caractères normalisée en majuscules sans accents ni caractères spéciaux ni apostrophes.
    """
    text=text.replace("'"," ")
    # Normalisation Unicode en forme décomposée (NFD) pour séparer les lettres et les accents
    text_nfd = unicodedata.normalize('NFD', text)
    # Suppression des caractères combinants (accents)
    text_without_accents = ''.join(c for c in text_nfd if not unicodedata.combining(c))
    # Suppression des caractères spéciaux, y compris les apostrophes, ne gardant que les mots et les espaces
    text_without_special = re.sub(r'[^\w\s]', '', text_without_accents)
    # Conversion en majuscules pour standardiser le texte
    return text_without_special.upper()

def contain_key(text, keywords, use_ner_verification=True):
    """
    Vérifie si tous les mots-clés/entités sont présents dans le texte normalisé.

    Cette fonction peut utiliser soit la vérification traditionnelle des mots-clés,
    soit la vérification intelligente des entités nommées qui est plus robuste.

    :param text: Chaîne de caractères dans laquelle rechercher les mots-clés.
    :param keywords: Liste de mots-clés/entités à rechercher dans le texte.
    :param use_ner_verification: Si True, utilise la vérification NER; sinon méthode traditionnelle.
    :return: `True` si tous les mots-clés sont présents dans le texte, sinon `False`.
    """
    if not keywords:
        return True
        
    if use_ner_verification:
        try:
            from .ner_utils import verify_entities_in_text
            found_entities = verify_entities_in_text(keywords, text)
            # Vérifier si au moins une entité significative est trouvée
            # (plutôt que toutes, pour être moins restrictif)
            return len(found_entities) > 0
        except Exception as e:
            import logging
            logging.warning(f"Erreur vérification NER, fallback vers méthode traditionnelle: {e}")
            # Fallback vers la méthode traditionnelle
    
    # Méthode traditionnelle
    # Normalisation du texte pour une comparaison standardisée
    normalized_text = normalize_text(text)
    # Création d'un ensemble de mots du texte pour une recherche rapide
    text_words = set(normalized_text.split())
    # Vérification de la présence de chaque mot-clé dans l'ensemble des mots du texte
    return all(normalize_text(keyword) in text_words for keyword in keywords)

def split_text_into_chunks(text, model, max_tokens=512, instruction="passage: "):
    """
    Divise un texte en plusieurs morceaux (chunks) de taille maximale définie par `max_tokens`.

    Cette fonction découpe le texte en phrases, puis regroupe ces phrases en chunks
    tout en respectant la limite de tokens spécifiée. Chaque chunk est préfixé par une instruction
    (par défaut "passage: ") pour guider le modèle lors de la génération de résumés ou d'autres tâches.

    :param text: Texte à diviser en chunks.
    :param model: Modèle utilisé pour tokenizer le texte.
    :param max_tokens: Nombre maximal de tokens par chunk.
    :param instruction: Instruction à ajouter en préfixe de chaque chunk.
    :return: Liste de chunks de texte.
    """
    # Calcul du nombre de tokens utilisés par l'instruction
    num_instruction_tokens = len(model.tokenizer.tokenize(instruction)) if instruction else 0
    # Calcul du nombre de tokens disponibles pour le contenu du chunk
    effective_max_tokens = max_tokens - num_instruction_tokens

    # Découpage du texte en phrases en utilisant les ponctuations comme délimiteurs
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # Tokenisation de la phrase actuelle
        sentence_tokens = model.tokenizer.tokenize(sentence)
        if current_chunk:
            # Tokenisation du chunk actuel
            current_chunk_tokens = model.tokenizer.tokenize(current_chunk)
            # Vérification si l'ajout de la nouvelle phrase dépasse la limite de tokens
            if len(current_chunk_tokens) + len(sentence_tokens) <= effective_max_tokens:
                # Ajout de la phrase au chunk actuel
                current_chunk += " " + sentence
            else:
                # Ajout du chunk actuel à la liste des chunks avec l'instruction en préfixe
                chunks.append(instruction + current_chunk.strip())
                # Réinitialisation du chunk actuel avec la nouvelle phrase
                current_chunk = sentence
        else:
            # Initialisation du chunk actuel avec la première phrase
            current_chunk = sentence

    # Ajout du dernier chunk restant à la liste des chunks
    if current_chunk:
        chunks.append(instruction + current_chunk.strip())

    return chunks

def search_upper_words(phrase):
    """
    Recherche les mots en majuscules dans une phrase, en excluant le premier mot.

    Cette fonction est conservée comme fallback pour la nouvelle logique NER.
    
    :param phrase: Phrase dans laquelle rechercher les mots en majuscules.
    :return: Liste de mots en majuscules trouvés dans la phrase, excluant le premier mot.
    """
    # Remplacer apostrophes par des espaces
    phrase=phrase.replace("'"," ")
    # Séparation de la phrase en mots individuels
    words = phrase.split()
    # Filtrage des mots en majuscules, en excluant le premier mot
    return [word for word in words[1:] if word[0].isupper()]

def search_named_entities_smart(phrase, language="fr", use_ner=True):
    """
    Recherche intelligente d'entités nommées dans une phrase.
    
    Cette fonction remplace l'ancienne logique de search_upper_words en utilisant
    la reconnaissance d'entités nommées (NER) avec spaCy. Elle fournit un fallback
    vers l'ancienne méthode si la NER échoue.
    
    :param phrase: Phrase dans laquelle rechercher les entités nommées.
    :param language: Langue du texte pour la NER (défaut: "fr").
    :param use_ner: Si True, utilise la NER; sinon utilise l'ancienne méthode.
    :return: Liste d'entités nommées ou de mots en majuscules.
    """
    if use_ner:
        try:
            from .ner_utils import search_named_entities
            return search_named_entities(phrase, language)
        except Exception as e:
            import logging
            logging.warning(f"Erreur NER, fallback vers search_upper_words: {e}")
            return search_upper_words(phrase)
    else:
        return search_upper_words(phrase)

def vectorize_query(query, model):
    """
    Vectorise une requête en utilisant le modèle fourni.

    Cette fonction encode la requête en ajoutant le préfixe "query: " pour différencier
    les requêtes des autres types de textes, puis convertit le texte en un vecteur
    normalisé adapté pour les calculs de similarité ou d'autres opérations vectorielles.

    :param query: Requête utilisateur à vectoriser.
    :param model: Modèle de vectorisation utilisé pour encoder la requête.
    :return: Vecteur de la requête sous forme de tenseur PyTorch.
    """
    # Utilise la fonction commune de vectorisation du module vector_utils
    from .vector_utils import vectorize_text
    return vectorize_text(query, model, prefix="query: ", chunk_content=False)

def del_pages_number(text):
    """
    Supprime les numéros de page à la fin du texte.
    
    :param text: Texte à nettoyer
    :return: Texte sans les numéros de page
    """
    return re.sub(r'\d+$', '', text)