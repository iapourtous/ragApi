"""
Utilitaires pour la gestion des embeddings de livres dans l'application RAG API.

Ce module fournit des fonctions pour calculer, stocker et rechercher des embeddings
de descriptions de livres pour optimiser la recherche sémantique.
"""
from datetime import datetime
from .vector_utils import vectorize_text, serialize_tensor, deserialize_tensor
from sentence_transformers import util
import torch
import logging

# Nom du modèle utilisé pour les embeddings
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-large"

def generate_description_embedding(description, model):
    """
    Génère l'embedding d'une description de livre.
    
    Args:
        description (str): Description du livre à vectoriser
        model: Modèle d'embedding (SentenceTransformer)
        
    Returns:
        tuple: (embedding_list, model_name, timestamp)
            - embedding_list: Vecteur sérialisé en liste
            - model_name: Nom du modèle utilisé
            - timestamp: Date de génération
    """
    if not description or not description.strip():
        return None, None, None
        
    try:
        # Utiliser vectorize_text avec le préfixe pour les passages
        embedding = vectorize_text(
            description.strip(), 
            model, 
            prefix="passage: ", 
            chunk_content=False,
            use_cache=True
        )
        
        # Sérialiser le tenseur en liste
        embedding_list = serialize_tensor(embedding)
        
        return embedding_list, EMBEDDING_MODEL_NAME, datetime.utcnow()
        
    except Exception as e:
        logging.error(f"Erreur lors de la génération de l'embedding : {e}")
        return None, None, None

def should_update_embedding(book_data, current_model_name=EMBEDDING_MODEL_NAME):
    """
    Détermine si l'embedding d'un livre doit être mis à jour.
    
    Args:
        book_data (dict): Données du livre
        current_model_name (str): Nom du modèle actuel
        
    Returns:
        bool: True si l'embedding doit être mis à jour
    """
    # Pas d'embedding existant
    if not book_data.get('description_embedding'):
        return bool(book_data.get('description'))
    
    # Modèle différent
    if book_data.get('description_embedding_model') != current_model_name:
        return True
    
    # Description modifiée après l'embedding (si on avait updated_at)
    # Pour l'instant, on se base sur l'existence
    return False

def search_books_by_embedding(query, all_books, model, top_k=5, threshold=0.5):
    """
    Recherche des livres par similarité d'embedding.
    
    Args:
        query (str): Requête de recherche
        all_books (list): Liste de tous les livres avec leurs embeddings
        model: Modèle d'embedding
        top_k (int): Nombre maximum de résultats à retourner
        threshold (float): Seuil de similarité minimum
        
    Returns:
        list: Liste des livres trouvés avec leurs scores de similarité
    """
    if not query or not query.strip():
        return []
    
    try:
        # Vectoriser la requête avec le préfixe approprié
        query_embedding = vectorize_text(
            query.strip(), 
            model, 
            prefix="query: ", 
            chunk_content=False,
            use_cache=True
        )
        
        # Filtrer les livres qui ont des embeddings et des descriptions
        books_with_embeddings = [
            book for book in all_books 
            if book.get('description_embedding') and book.get('description')
        ]
        
        if not books_with_embeddings:
            logging.warning("Aucun livre avec embedding trouvé pour la recherche")
            return []
        
        # Convertir les embeddings stockés en tenseurs
        book_embeddings = []
        for book in books_with_embeddings:
            try:
                embedding_tensor = deserialize_tensor(book['description_embedding'], query_embedding.device)
                book_embeddings.append(embedding_tensor)
            except Exception as e:
                logging.error(f"Erreur de désérialisation pour le livre {book.get('_id')}: {e}")
                continue
        
        if not book_embeddings:
            logging.warning("Aucun embedding valide trouvé")
            return []
        
        # Calculer les similarités
        book_embeddings_tensor = torch.stack(book_embeddings)
        similarities = util.cos_sim(query_embedding, book_embeddings_tensor)
        similarities = similarities.flatten().cpu().numpy()
        
        # Créer la liste des résultats avec scores
        results = []
        for i, (book, similarity) in enumerate(zip(books_with_embeddings, similarities)):
            if similarity >= threshold:
                results.append({
                    **book,
                    'similarity_score': float(similarity)
                })
        
        # Trier par score décroissant et limiter aux top_k
        results = sorted(results, key=lambda x: x['similarity_score'], reverse=True)[:top_k]
        
        logging.info(f"Recherche terminée: {len(results)} résultats trouvés pour '{query}'")
        return results
        
    except Exception as e:
        logging.error(f"Erreur lors de la recherche par embedding : {e}")
        return []

def calculate_embedding_stats(books):
    """
    Calcule des statistiques sur les embeddings des livres.
    
    Args:
        books (list): Liste des livres
        
    Returns:
        dict: Statistiques des embeddings
    """
    total_books = len(books)
    books_with_embeddings = sum(
        1 for book in books 
        if book.get('description_embedding') and len(book.get('description_embedding', [])) > 0
    )
    books_with_descriptions = sum(1 for book in books if book.get('description'))
    books_needing_embeddings = sum(
        1 for book in books 
        if book.get('description') and (
            not book.get('description_embedding') or 
            len(book.get('description_embedding', [])) == 0
        )
    )
    
    return {
        'total_books': total_books,
        'books_with_embeddings': books_with_embeddings,
        'books_with_descriptions': books_with_descriptions,
        'books_needing_embeddings': books_needing_embeddings,
        'embedding_coverage': books_with_embeddings / max(books_with_descriptions, 1) * 100
    }