"""
Module d'utilitaires pour les opérations sur les vecteurs dans l'application RAG API.

Ce module fournit des fonctions pour la manipulation, la sérialisation et la comparaison
de vecteurs d'embeddings. Il inclut des utilitaires pour calculer les similitudes cosinus,
vectoriser des pages de documents, sérialiser et désérialiser des tenseurs PyTorch, et
comparer des requêtes textuelles à des descriptions vectorisées. Ces fonctions sont
essentielles pour le cœur de fonctionnalité RAG (Retrieval Augmented Generation) de
l'application.
"""
from .text_utils import contain_key, search_upper_words, split_text_into_chunks
import torch
from sentence_transformers import util
import numpy as np
import logging
from .cache_utils import vector_cache

def vectorize_text(text, model, prefix="", chunk_content=True, use_cache=True, device=None):
    """
    Fonction de base pour vectoriser du texte avec mise en cache.
    
    Convertit un texte en vecteur d'embedding en utilisant le modèle spécifié.
    Si chunk_content est True, le texte est divisé en chunks avant vectorisation.
    Utilise un cache pour éviter de recalculer les embeddings des textes déjà traités.
    
    :param text: Texte à vectoriser
    :param model: Modèle d'embedding à utiliser
    :param prefix: Préfixe optionnel à ajouter au texte (ex: "query: ", "passage: ")
    :param chunk_content: Si True, diviser le texte en chunks avant de vectoriser
    :param use_cache: Si True, utilise le cache de vectorisation
    :param device: Device sur lequel placer le tenseur résultant (None = laisser sur le device par défaut)
    :return: Tenseur ou liste de tenseurs selon chunk_content
    """
    # Vérifier si le résultat est déjà dans le cache
    if use_cache:
        cached_result = vector_cache.get(text, prefix, chunk_content, device)
        if cached_result is not None:
            return cached_result
    
    # Si pas dans le cache, procéder à la vectorisation
    if chunk_content:
        # Division du texte en chunks respectant la limite de tokens
        chunked_text = split_text_into_chunks(text, model)
        # Encodage de chaque chunk en vecteurs
        embeddings = [model.encode(prefix + chunk, convert_to_tensor=True, normalize_embeddings=True) 
                     for chunk in chunked_text]
        
        # Mettre en cache chaque chunk si nécessaire
        if use_cache:
            for i, chunk in enumerate(chunked_text):
                vector_cache.put(chunk, embeddings[i], prefix, False)
                
        return embeddings
    else:
        # Encodage du texte complet
        embedding = model.encode(prefix + text, convert_to_tensor=True, normalize_embeddings=True)
        
        # Mettre en cache le résultat si nécessaire
        if use_cache:
            vector_cache.put(text, embedding, prefix, chunk_content)
            
        # Déplacer sur le device demandé si nécessaire
        if device is not None:
            embedding = embedding.to(device)
            
        return embedding

def calculate_similarity(data, vector_to_compare, device):
    """
    Calcule la similarité entre les vecteurs donnés et un vecteur de comparaison en utilisant la similarité cosinus.

    Cette fonction traite les données en lots pour optimiser les calculs de similarité. Elle retourne
    une liste de scores de similarité associés aux métadonnées correspondantes.

    :param data: Liste de dictionnaires contenant les données et leurs vecteurs associés.
    :param vector_to_compare: Tenseur PyTorch représentant le vecteur de comparaison.
    :param device: Appareil ('cpu' ou 'cuda') sur lequel effectuer les calculs.
    :return: Liste de dictionnaires contenant les scores de similarité et les métadonnées.
    """
    # Déplace le vecteur de comparaison sur l'appareil spécifié une seule fois
    vector_to_compare = vector_to_compare.to(device)

    # Listes pour stocker tous les vecteurs et leurs indices correspondants
    all_vectors = []
    item_indices = []

    # Collecte de tous les vecteurs et suivi de leur index d'élément
    for idx, item in enumerate(data):
        # Désérialisation des vecteurs stockés et déplacement sur l'appareil spécifié
        vectors = [deserialize_tensor(vec, device) for vec in item["vector_data"]]
        all_vectors.extend(vectors)
        # Suivi de l'index de l'élément pour chaque vecteur
        item_indices.extend([idx] * len(vectors))

    # Vérifie s'il y a des vecteurs à comparer
    if not all_vectors:
        return []

    # Empile tous les vecteurs en un seul tenseur
    all_vectors_tensor = torch.stack(all_vectors)  # Forme : (nombre_vecteurs, dimension_vecteur)

    # Calcule les similarités cosinus en une seule opération
    similarities = util.cos_sim(all_vectors_tensor, vector_to_compare)  # Forme : (nombre_vecteurs, 1)
    similarities = similarities.flatten()

    # Dictionnaire pour stocker le meilleur score pour chaque élément
    item_best_scores = {}

    # Trouve le meilleur score pour chaque élément
    for sim, idx in zip(similarities.tolist(), item_indices):
        if idx not in item_best_scores or sim > item_best_scores[idx]:
            item_best_scores[idx] = sim

    # Construction de la liste des scores avec les métadonnées associées
    scores = []
    for idx, item in enumerate(data):
        best_score = item_best_scores.get(idx, 0.0)
        scores.append({
            "score": best_score,
            "pageBegin": item.get("pageBegin", ''),
            "pageEnd": item.get("pageEnd", ''),
            "summary": item.get("resume", ''),
            "text": item.get("text", ''),
            "pageNumber": item.get("pageNumber", ''),
            "file": item['file']
        })

    return scores

def deserialize_tensor(tensor_bytes, device):
    """
    Désérialise une liste en un tenseur PyTorch.

    :param tensor_bytes: Liste représentant le tenseur.
    :param device: Appareil ('cpu' ou 'cuda') sur lequel charger le tenseur.
    :return: Tenseur PyTorch.
    """
    return torch.tensor(tensor_bytes).to(device)

def get_top_scores(scores, n, threshold):
    """
    Récupère les meilleurs scores au-dessus d'un seuil donné.

    :param scores: Liste de scores.
    :param n: Nombre de meilleurs scores à récupérer.
    :param threshold: Seuil minimal qu'un score doit dépasser pour être considéré.
    :return: Liste des meilleurs scores filtrés.
    """
    return [s for s in sorted(scores, key=lambda x: x['score'], reverse=True) if s['score'] > threshold][:n]

def vectorize_pages(doc, begin, end, model):
    """
    Vectorise les pages d'un document PDF.

    Cette fonction extrait le texte des pages spécifiées, le divise en chunks, encode chaque chunk
    en vecteurs à l'aide du modèle fourni, et stocke les vecteurs sérialisés.

    :param doc: Document PDF (objet PyMuPDF).
    :param begin: Numéro de la première page à traiter (1-indexé).
    :param end: Numéro de la dernière page à traiter (1-indexé).
    :param model: Modèle de vectorisation utilisé pour encoder le texte.
    :return: Liste de dictionnaires contenant les informations vectorisées des pages.
    """
    pages = []
    for page in doc[begin-1:end]:
        # Extraction du texte de la page
        text = page.get_text()
        # Utilisation de la fonction commune de vectorisation avec cache
        embeddings = vectorize_text(text, model, prefix="passage: ", chunk_content=True)
        pages.append({
            "pageNumber": page.number,
            "text": text,
            "vector_data": [serialize_tensor(e) for e in embeddings]
        })
    return pages

def serialize_tensor(tensor):
    """
    Sérialise un tenseur PyTorch en une liste.

    :param tensor: Tenseur PyTorch à sérialiser.
    :return: Liste représentant le tenseur.
    """
    return tensor.tolist()

def compare_query_to_descriptions(query, descriptions, descriptions_vectorized, model, device):
    """
    Compare une requête aux descriptions en utilisant les vecteurs pré-calculés.

    Cette fonction calcule la similarité entre la requête vectorisée et les vecteurs des descriptions.
    Elle prend en compte les mots-clés en majuscules pour filtrer les descriptions pertinentes.

    :param query: La requête utilisateur.
    :param descriptions: Liste de listes de descriptions.
    :param descriptions_vectorized: Liste de listes de vecteurs correspondants aux descriptions.
    :param model: Modèle utilisé pour vectoriser la requête.
    :param device: Appareil ('cpu' ou 'cuda') pour le calcul des similarités.
    :return: Liste de similarités structurées comme les descriptions.
    """
    # Étape 1 : Extraire les mots en majuscules de la requête (excluant le premier mot)
    uppercase_words = search_upper_words(query)

    # Initialiser la structure des similarités avec des zéros 
    normalized_similarities = [
        [0.0 for _ in level] for level in descriptions
    ]

    # Aplatir les descriptions et les vecteurs
    flat_descriptions = []
    for level in descriptions:
        for desc in level:
            # Vérifier si desc est un dictionnaire et extraire le texte
            if isinstance(desc, dict):
                flat_descriptions.append(desc['text'])
            else:
                flat_descriptions.append(desc)
                
    flat_vectors = [deserialize_tensor(vec, device) for level in descriptions_vectorized for vec in level]

    # Vectoriser la requête en utilisant notre fonction commune (avec cache)
    query_embedding = vectorize_text(query, model, prefix="query: ", chunk_content=False, device=device)

    if uppercase_words:
        # Créer une liste booléenne indiquant si chaque description contient un mot en majuscule
        contains_uppercase = [contain_key(desc, uppercase_words) for desc in flat_descriptions]

        # Indices des descriptions à traiter
        indices_to_process = [i for i, contains in enumerate(contains_uppercase) if contains]

        if indices_to_process:
            # Extraire les vecteurs à traiter
            matching_embeddings = [flat_vectors[i] for i in indices_to_process]

            # Calculer les similarités
            similarities = util.cos_sim(query_embedding, torch.stack(matching_embeddings)).cpu().numpy().flatten()

            # Normaliser les similarités entre 0 et 1
            min_sim = similarities.min()
            max_sim = similarities.max()
            if max_sim != min_sim:
                normalized = (similarities - min_sim) / (max_sim - min_sim)
            else:
                normalized = np.zeros_like(similarities)

            # Convertir les similarités normalisées en float natif
            normalized = [float(sim) for sim in normalized]

            # Réintégrer les similarités normalisées dans la structure 2D
            cumulative = 0
            normalized_idx = 0
            for level_idx, level in enumerate(descriptions):
                for desc_idx in range(len(level)):
                    if cumulative in indices_to_process:
                        sim = normalized[normalized_idx]
                        normalized_similarities[level_idx][desc_idx] = sim
                        normalized_idx += 1
                    cumulative += 1
    else:
        # Calculer les similarités pour toutes les descriptions
        if flat_vectors:
            similarities = util.cos_sim(query_embedding, torch.stack(flat_vectors)).cpu().numpy().flatten()

            # Normaliser les similarités entre 0 et 1
            min_sim = similarities.min()
            max_sim = similarities.max()
            if max_sim != min_sim:
                normalized = (similarities - min_sim) / (max_sim - min_sim)
            else:
                normalized = np.zeros_like(similarities)

            # Convertir les similarités normalisées en float natif
            normalized = [float(sim) for sim in normalized]

            # Réorganiser les similarités normalisées dans la structure 2D originale
            idx = 0
            for level_idx, level in enumerate(descriptions):
                for desc_idx in range(len(level)):
                    normalized_similarities[level_idx][desc_idx] = normalized[idx]
                    idx += 1

    return normalized_similarities

def get_cache_stats():
    """
    Récupère les statistiques du cache de vectorisation.
    
    :return: Statistiques du cache de vecteurs
    """
    return vector_cache.get_stats()