"""
Module de Data Transfer Objects (DTO) pour la recherche de livres par embedding.

Ce module contient les classes DTO pour structurer les requêtes et réponses
de recherche sémantique de livres.
"""
from typing import List, Optional, Dict, Any
from .book_dto import BookResponseDTO

class BookSearchRequestDTO:
    """
    DTO pour les requêtes de recherche de livres par embedding.
    """
    
    def __init__(self, query: str, k: int = 5, threshold: float = 0.5, 
                 category: Optional[str] = None, author: Optional[str] = None):
        """
        Initialise une requête de recherche de livres.
        
        Args:
            query (str): Texte de la requête de recherche
            k (int): Nombre maximum de résultats à retourner (défaut: 5)
            threshold (float): Seuil de similarité minimum entre 0 et 1 (défaut: 0.5)
            category (str, optional): Filtrer par catégorie
            author (str, optional): Filtrer par auteur
        """
        self.query = query
        self.k = max(1, min(k, 50))  # Limiter entre 1 et 50
        self.threshold = max(0.0, min(threshold, 1.0))  # Limiter entre 0 et 1
        self.category = category
        self.author = author
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookSearchRequestDTO':
        """
        Crée une instance à partir d'un dictionnaire.
        
        Args:
            data (dict): Dictionnaire contenant les données de la requête
            
        Returns:
            BookSearchRequestDTO: Instance créée
        """
        return cls(
            query=data.get('query', ''),
            k=data.get('k', 5),
            threshold=data.get('threshold', 0.5),
            category=data.get('category'),
            author=data.get('author')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance en dictionnaire.
        
        Returns:
            dict: Dictionnaire contenant les données de la requête
        """
        data = {
            'query': self.query,
            'k': self.k,
            'threshold': self.threshold
        }
        if self.category:
            data['category'] = self.category
        if self.author:
            data['author'] = self.author
        return data
    
    def is_valid(self) -> bool:
        """
        Valide la requête de recherche.
        
        Returns:
            bool: True si la requête est valide
        """
        return bool(self.query and self.query.strip())

class BookSearchResultDTO:
    """
    DTO pour un résultat de recherche de livre.
    """
    
    def __init__(self, book: BookResponseDTO, similarity_score: float):
        """
        Initialise un résultat de recherche.
        
        Args:
            book (BookResponseDTO): Informations du livre
            similarity_score (float): Score de similarité (0-1)
        """
        self.book = book
        self.similarity_score = similarity_score
    
    @classmethod
    def from_book_data(cls, book_data: Dict[str, Any]) -> 'BookSearchResultDTO':
        """
        Crée une instance à partir des données d'un livre avec score.
        
        Args:
            book_data (dict): Données du livre incluant similarity_score
            
        Returns:
            BookSearchResultDTO: Instance créée
        """
        similarity_score = book_data.pop('similarity_score', 0.0)
        
        book_dto = BookResponseDTO(
            id=book_data.get('_id', ''),
            title=book_data.get('title', ''),
            author=book_data.get('author', ''),
            description=book_data.get('description'),
            cover_image=book_data.get('cover_image'),
            filename=book_data.get('pdf_path'),
            owner_id=book_data.get('proprietary'),
            public=book_data.get('public', False),
            created_at=book_data.get('created_at'),
            updated_at=book_data.get('updated_at'),
            category=book_data.get('category'),
            subcategory=book_data.get('subcategory')
        )
        
        return cls(book_dto, similarity_score)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance en dictionnaire.
        
        Returns:
            dict: Dictionnaire contenant le livre et son score
        """
        return {
            'book': self.book.to_dict(),
            'similarity_score': self.similarity_score
        }

class BookSearchResponseDTO:
    """
    DTO pour la réponse complète de recherche de livres.
    """
    
    def __init__(self, results: List[BookSearchResultDTO], query: str, 
                 total_found: int, execution_time: Optional[float] = None):
        """
        Initialise une réponse de recherche.
        
        Args:
            results (List[BookSearchResultDTO]): Liste des résultats trouvés
            query (str): Requête originale
            total_found (int): Nombre total de résultats trouvés
            execution_time (float, optional): Temps d'exécution en secondes
        """
        self.results = results
        self.query = query
        self.total_found = total_found
        self.execution_time = execution_time
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance en dictionnaire.
        
        Returns:
            dict: Dictionnaire contenant la réponse complète
        """
        data = {
            'results': [result.to_dict() for result in self.results],
            'query': self.query,
            'total_found': self.total_found,
            'returned_count': len(self.results)
        }
        if self.execution_time is not None:
            data['execution_time'] = self.execution_time
        return data

class EmbeddingStatsDTO:
    """
    DTO pour les statistiques des embeddings.
    """
    
    def __init__(self, total_books: int, books_with_embeddings: int, 
                 books_with_descriptions: int, books_needing_embeddings: int,
                 embedding_coverage: float):
        """
        Initialise les statistiques d'embeddings.
        
        Args:
            total_books (int): Nombre total de livres
            books_with_embeddings (int): Nombre de livres avec embeddings
            books_with_descriptions (int): Nombre de livres avec descriptions
            books_needing_embeddings (int): Nombre de livres nécessitant un embedding
            embedding_coverage (float): Pourcentage de couverture des embeddings
        """
        self.total_books = total_books
        self.books_with_embeddings = books_with_embeddings
        self.books_with_descriptions = books_with_descriptions
        self.books_needing_embeddings = books_needing_embeddings
        self.embedding_coverage = embedding_coverage
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmbeddingStatsDTO':
        """
        Crée une instance à partir d'un dictionnaire.
        
        Args:
            data (dict): Dictionnaire contenant les statistiques
            
        Returns:
            EmbeddingStatsDTO: Instance créée
        """
        return cls(
            total_books=data.get('total_books', 0),
            books_with_embeddings=data.get('books_with_embeddings', 0),
            books_with_descriptions=data.get('books_with_descriptions', 0),
            books_needing_embeddings=data.get('books_needing_embeddings', 0),
            embedding_coverage=data.get('embedding_coverage', 0.0)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit l'instance en dictionnaire.
        
        Returns:
            dict: Dictionnaire contenant les statistiques
        """
        return {
            'total_books': self.total_books,
            'books_with_embeddings': self.books_with_embeddings,
            'books_with_descriptions': self.books_with_descriptions,
            'books_needing_embeddings': self.books_needing_embeddings,
            'embedding_coverage': round(self.embedding_coverage, 2)
        }