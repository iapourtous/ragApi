"""
Module de définition du modèle de données pour les livres dans l'application RAG API.

Ce module contient la classe DBBook qui représente un livre dans la base de données
MongoDB. Il fournit les méthodes pour créer, sérialiser et désérialiser des objets
livre, avec leurs métadonnées et chemins vers les ressources associées.
"""
from datetime import datetime

class DBBook:
    """
    Représente un livre dans la base de données avec ses métadonnées associées.
    
    Cette classe gère les informations relatives à un livre, incluant ses métadonnées,
    son emplacement dans le système de fichiers, et ses propriétés descriptives.

    Attributes:
        _id (str): Identifiant unique du livre dans la base de données
        title (str): Titre du livre
        author (str): Auteur du livre
        publication_year (int): Année de publication
        description (str): Description ou résumé du livre
        category (str): Catégorie principale du livre
        subcategory (str): Sous-catégorie du livre
        edition (str): Information sur l'édition du livre
        proprietary (str): Propriétaire ou gestionnaire du livre
        cover_image (str): Chemin vers l'image de couverture
        pdf_path (str): Chemin vers le fichier PDF
        db_path (str): Chemin vers les données traitées du livre
        begin (int): Page de début pour le traitement
        end (int): Page de fin pour le traitement
        directory (str): Répertoire de stockage du livre
        metadata (dict): Métadonnées additionnelles
        created_at (datetime): Date et heure de création de l'entrée
        illustration (bool): Indique si le livre contient des illustrations à traiter
        description_embedding (list): Vecteur d'embedding de la description
        description_embedding_model (str): Nom du modèle utilisé pour l'embedding
        description_embedding_date (datetime): Date de calcul de l'embedding
    """

    def __init__(self, title, author=None, publication_year=None, description=None,
                 category=None, subcategory=None, edition=None, proprietary=None,
                 cover_image=None, pdf_path=None, db_path=None, begin=None, end=None,
                 directory=None, metadata=None, created_at=None, _id=None, illustration=False,
                 public=True, description_embedding=None, description_embedding_model=None, description_embedding_date=None):
        """
        Initialise une nouvelle instance de DBBook.

        Args:
            title (str): Titre du livre
            author (str, optional): Auteur du livre
            publication_year (int, optional): Année de publication
            description (str, optional): Description ou résumé du livre
            category (str, optional): Catégorie principale du livre
            subcategory (str, optional): Sous-catégorie du livre
            edition (str, optional): Information sur l'édition
            proprietary (str, optional): Propriétaire ou gestionnaire
            cover_image (str, optional): Chemin vers l'image de couverture
            pdf_path (str, optional): Chemin vers le fichier PDF
            db_path (str, optional): Chemin vers les données traitées
            begin (int, optional): Page de début pour le traitement
            end (int, optional): Page de fin pour le traitement
            directory (str, optional): Répertoire de stockage
            metadata (dict, optional): Métadonnées additionnelles
            created_at (datetime, optional): Date et heure de création
            _id (str, optional): Identifiant unique dans la base de données
            illustration (bool, optional): Présence d'illustrations à traiter
            description_embedding (list, optional): Vecteur d'embedding de la description
            description_embedding_model (str, optional): Nom du modèle utilisé
            description_embedding_date (datetime, optional): Date de calcul de l'embedding
        """
        self._id = _id
        self.title = title
        self.author = author
        self.publication_year = publication_year
        self.description = description
        self.category = category
        self.subcategory = subcategory
        self.edition = edition
        self.proprietary = proprietary
        self.cover_image = cover_image
        self.pdf_path = pdf_path
        self.db_path = db_path
        self.begin = begin
        self.end = end
        self.directory = directory
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.illustration = illustration
        self.public = public
        self.description_embedding = description_embedding
        self.description_embedding_model = description_embedding_model
        self.description_embedding_date = description_embedding_date

    @staticmethod
    def from_dict(data):
        """
        Crée une instance de DBBook à partir d'un dictionnaire.

        Cette méthode permet de créer une instance de DBBook à partir de données
        structurées, typiquement issues de la base de données.

        Args:
            data (dict): Dictionnaire contenant les données du livre

        Returns:
            DBBook: Une nouvelle instance de DBBook initialisée avec les données fournies
        """
        return DBBook(
            _id=data.get('_id'),
            title=data.get('title'),
            author=data.get('author'),
            publication_year=data.get('publication_year'),
            description=data.get('description'),
            category=data.get('category'),
            subcategory=data.get('subcategory'),
            edition=data.get('edition'),
            proprietary=data.get('proprietary'),
            cover_image=data.get('cover_image'),
            pdf_path=data.get('pdf_path'),
            db_path=data.get('db_path'),
            begin=data.get('begin'),
            end=data.get('end'),
            directory=data.get('directory'),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at'),
            illustration=data.get('illustration', False),
            description_embedding=data.get('description_embedding'),
            description_embedding_model=data.get('description_embedding_model'),
            description_embedding_date=data.get('description_embedding_date')
        )

    def to_dict(self):
        """
        Convertit l'instance en dictionnaire.

        Cette méthode sérialise l'objet DBBook en un dictionnaire, utile pour
        le stockage en base de données ou la transmission via API.

        Returns:
            dict: Dictionnaire contenant toutes les données du livre
        """
        data = {
            'title': self.title,
            'author': self.author,
            'publication_year': self.publication_year,
            'description': self.description,
            'category': self.category,
            'subcategory': self.subcategory,
            'edition': self.edition,
            'proprietary': self.proprietary,
            'cover_image': self.cover_image,
            'pdf_path': self.pdf_path,
            'db_path': self.db_path,
            'begin': self.begin,
            'end': self.end,
            'directory': self.directory,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'illustration': self.illustration,
            'public': self.public,
            'description_embedding': self.description_embedding,
            'description_embedding_model': self.description_embedding_model,
            'description_embedding_date': self.description_embedding_date
        }
        if self._id:
            data['_id'] = self._id
        return data