"""
DTOs pour la gestion des livres.
"""
from typing import Optional, Dict, Any, List


class BookCreationRequestDTO:
    """DTO pour la requête de création d'un livre."""
    
    def __init__(self, title: str, author: str, 
                 description: Optional[str] = None, 
                 cover_image: Optional[str] = None, 
                 filename: Optional[str] = None,
                 public: bool = False):
        """
        Initialise une requête de création de livre.
        
        Params:
            title: Titre du livre
            author: Auteur du livre
            description: Description du livre (optionnel)
            cover_image: Image de couverture (optionnel)
            filename: Nom du fichier PDF (optionnel)
            public: Indique si le livre est public (par défaut: False)
        """
        self.title = title
        self.author = author
        self.description = description
        self.cover_image = cover_image
        self.filename = filename
        self.public = public
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookCreationRequestDTO':
        """
        Crée un DTO à partir d'un dictionnaire.
        
        Params:
            data: Dictionnaire contenant les données
            
        Returns:
            Instance du DTO
        """
        return cls(
            title=data.get('title', ''),
            author=data.get('author', ''),
            description=data.get('description'),
            cover_image=data.get('coverImage'),
            filename=data.get('filename'),
            public=data.get('public', False)
        )


class BookUpdateRequestDTO:
    """DTO pour la requête de mise à jour d'un livre."""
    
    def __init__(self, title: Optional[str] = None, 
                 author: Optional[str] = None,
                 description: Optional[str] = None, 
                 cover_image: Optional[str] = None,
                 public: Optional[bool] = None):
        """
        Initialise une requête de mise à jour de livre.
        
        Params:
            title: Titre du livre (optionnel)
            author: Auteur du livre (optionnel)
            description: Description du livre (optionnel)
            cover_image: Image de couverture (optionnel)
            public: Indique si le livre est public (optionnel)
        """
        self.title = title
        self.author = author
        self.description = description
        self.cover_image = cover_image
        self.public = public
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookUpdateRequestDTO':
        """
        Crée un DTO à partir d'un dictionnaire.
        
        Params:
            data: Dictionnaire contenant les données
            
        Returns:
            Instance du DTO
        """
        return cls(
            title=data.get('title'),
            author=data.get('author'),
            description=data.get('description'),
            cover_image=data.get('coverImage'),
            public=data.get('public')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le DTO en dictionnaire, en excluant les valeurs None.
        
        Returns:
            Dictionnaire représentant le DTO
        """
        result = {}
        if self.title is not None:
            result['title'] = self.title
        if self.author is not None:
            result['author'] = self.author
        if self.description is not None:
            result['description'] = self.description
        if self.cover_image is not None:
            result['coverImage'] = self.cover_image
        if self.public is not None:
            result['public'] = self.public
        return result


class BookResponseDTO:
    """DTO pour la réponse de livre."""
    
    def __init__(self, id: str, title: str, author: str, 
                 description: Optional[str] = None,
                 cover_image: Optional[str] = None,
                 filename: Optional[str] = None,
                 owner_id: str = None,
                 public: bool = False,
                 created_at: Optional[str] = None,
                 updated_at: Optional[str] = None,
                 category: Optional[str] = None,
                 subcategory: Optional[str] = None):
        """
        Initialise une réponse de livre.
        
        Params:
            id: Identifiant du livre
            title: Titre du livre
            author: Auteur du livre
            description: Description du livre (optionnel)
            cover_image: Image de couverture (optionnel)
            filename: Nom du fichier PDF (optionnel)
            owner_id: Identifiant du propriétaire (optionnel)
            public: Indique si le livre est public (par défaut: False)
            created_at: Date de création (optionnel)
            updated_at: Date de mise à jour (optionnel)
            category: Catégorie du livre (optionnel)
            subcategory: Sous-catégorie du livre (optionnel)
        """
        self.id = id
        self.title = title
        self.author = author
        self.description = description
        self.cover_image = cover_image
        self.filename = filename
        self.owner_id = owner_id
        self.public = public
        self.created_at = created_at
        self.updated_at = updated_at
        self.category = category
        self.subcategory = subcategory
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookResponseDTO':
        """
        Crée un DTO à partir d'un dictionnaire.
        
        Params:
            data: Dictionnaire contenant les données
            
        Returns:
            Instance du DTO
        """
        return cls(
            id=data.get('_id', ''),
            title=data.get('title', ''),
            author=data.get('author', ''),
            description=data.get('description'),
            cover_image=data.get('coverImage'),
            filename=data.get('filename'),
            owner_id=data.get('ownerId'),
            public=data.get('public', False),
            created_at=data.get('createdAt'),
            updated_at=data.get('updatedAt'),
            category=data.get('category'),
            subcategory=data.get('subcategory')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le DTO en dictionnaire.
        
        Returns:
            Dictionnaire représentant le DTO
        """
        # Format compatible avec l'API existante
        result = {
            '_id': self.id,  # Utiliser _id au lieu de id
            'title': self.title,
            'author': self.author,
            'public': self.public
        }
        
        if self.description:
            result['description'] = self.description
        if self.cover_image:
            result['cover_image'] = self.cover_image  # Utiliser cover_image au lieu de coverImage
        if self.filename:
            result['pdf_path'] = self.filename  # Utiliser pdf_path au lieu de filename
        if self.owner_id:
            result['proprietary'] = self.owner_id  # Utiliser proprietary au lieu de ownerId
        if self.created_at:
            result['created_at'] = self.created_at  # Utiliser created_at au lieu de createdAt
        if self.updated_at:
            result['updated_at'] = self.updated_at  # Utiliser updated_at au lieu de updatedAt
        if self.category:
            result['category'] = self.category
        if self.subcategory:
            result['subcategory'] = self.subcategory
            
        return result


class BookListResponseDTO:
    """DTO pour la réponse de liste de livres."""
    
    def __init__(self, books: List[BookResponseDTO], total: int, page: int, per_page: int):
        """
        Initialise une réponse de liste de livres.
        
        Params:
            books: Liste des livres
            total: Nombre total de livres
            page: Page actuelle
            per_page: Nombre de livres par page
        """
        self.books = books
        self.total = total
        self.page = page
        self.per_page = per_page
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le DTO en dictionnaire.
        
        Returns:
            Dictionnaire représentant le DTO
        """
        # Compatibilité avec l'API existante qui s'attend à avoir un champ 'books'
        # directement au premier niveau
        return {
            'books': [book.to_dict() for book in self.books],
            'total': self.total,
            'page': self.page,
            'perPage': self.per_page
        }


class GenerateCoverRequestDTO:
    """DTO pour la requête de génération de couverture."""
    
    def __init__(self, filename: str):
        """
        Initialise une requête de génération de couverture.
        
        Params:
            filename: Nom du fichier PDF
        """
        self.filename = filename
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GenerateCoverRequestDTO':
        """
        Crée un DTO à partir d'un dictionnaire.
        
        Params:
            data: Dictionnaire contenant les données
            
        Returns:
            Instance du DTO
        """
        return cls(
            filename=data.get('filename', '')
        )


class DescriptionGenerationRequestDTO:
    """DTO pour la requête de génération de description."""
    
    def __init__(self, pdf_files: List[str], context: Optional[str] = None):
        """
        Initialise une requête de génération de description.
        
        Params:
            pdf_files: Liste des fichiers PDF
            context: Contexte pour la génération (optionnel)
        """
        self.pdf_files = pdf_files
        self.context = context
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DescriptionGenerationRequestDTO':
        """
        Crée un DTO à partir d'un dictionnaire.
        
        Params:
            data: Dictionnaire contenant les données
            
        Returns:
            Instance du DTO
        """
        return cls(
            pdf_files=data.get('pdf_files', []),
            context=data.get('context')
        )