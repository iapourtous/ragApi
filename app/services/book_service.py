from ..mongoClient import Client
from ..models.db_book import DBBook
from bson import ObjectId
import logging

__all__ = ['BookService']

class BookService:
    """
    Service gérant les opérations CRUD pour les livres dans la base de données.
    
    Cette classe fournit une interface pour interagir avec la collection de livres,
    permettant la création, la lecture, la mise à jour et la suppression de livres,
    ainsi que des recherches spécifiques par différents critères.
    """

    def __init__(self):
        """
        Initialise le service avec une connexion à la base de données.
        
        Établit une connexion à la base de données MongoDB et initialise
        la collection des livres.
        """
        self.client = Client("rag")
        self.books_collection = self.client.get_collection("books")

    def create_book(self, book_data):
        """
        Crée un nouveau livre dans la base de données.
        
        Args:
            book_data (dict): Dictionnaire contenant les données du livre à créer.
                Doit inclure au minimum :
                - title (str): Titre du livre
                - pdf_path (str): Chemin vers le fichier PDF
                Peut inclure :
                - author (str): Auteur du livre
                - edition (str): Édition du livre
                - proprietary (str): Propriétaire du livre
                - cover_image (str): Chemin vers l'image de couverture
                - category (str): Catégorie du livre
                - subcategory (str): Sous-catégorie du livre
                - directory (str): Répertoire de stockage
                - metadata (dict): Métadonnées additionnelles
                
        Returns:
            str: ID du livre créé ou None en cas d'erreur
        """
        try:
            db_book = DBBook(**book_data)
            result = self.books_collection.insert_one(db_book.to_dict())
            logging.info(f"Livre créé avec l'ID : {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logging.error(f"Erreur lors de la création du livre : {e}")
            return None

    def get_book(self, book_id):
        """
        Récupère un livre par son ID.
        
        Args:
            book_id (str): ID du livre à récupérer
            
        Returns:
            dict: Données du livre ou None si non trouvé
        """
        try:
            book_data = self.books_collection.find_one({"_id": ObjectId(book_id)})
            if book_data:
                book_data["_id"] = str(book_data["_id"])
                return book_data
            return None
        except Exception as e:
            logging.error(f"Erreur lors de la récupération du livre : {e}")
            return None
            
    def get_book_by_id(self, book_id):
        """
        Récupère un livre par son ID et le convertit en objet DBBook.
        
        Args:
            book_id (str): ID du livre à récupérer
            
        Returns:
            dict: Données du livre ou None si non trouvé
        """
        try:
            book_data = self.books_collection.find_one({"_id": ObjectId(book_id)})
            if book_data:
                book_data["_id"] = str(book_data["_id"])
                return DBBook.from_dict(book_data).to_dict()
            return None
        except Exception as e:
            logging.error(f"Erreur lors de la récupération du livre par ID : {e}")
            return None

    def get_all_books(self, current_user):
        """
        Récupère tous les livres accessibles à l'utilisateur.
        
        Les livres retournés dépendent du rôle de l'utilisateur :
        - Les administrateurs voient tous les livres
        - Les utilisateurs normaux voient leurs livres et les livres publics
        
        Args:
            current_user (dict): Informations sur l'utilisateur courant
                Doit contenir :
                - username (str): Nom d'utilisateur
                - role (str): Rôle de l'utilisateur
                
        Returns:
            list: Liste des livres accessibles à l'utilisateur
        """
        try:
            books = []
            cursor = None
            if current_user['role'] != "admin":
                cursor = self.books_collection.find({
                    "$or": [
                        {"proprietary": current_user['username']},
                        {"public": True}  # Utiliser le champ public au lieu de proprietary
                    ]
                })
            else:
                cursor = self.books_collection.find()

            for book_data in cursor:
                book_data["_id"] = str(book_data["_id"])
                books.append(DBBook.from_dict(book_data).to_dict())
            return books
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des livres : {e}")
            return []

    def update_book(self, book_id, update_data):
        """
        Met à jour les informations d'un livre.
        
        Args:
            book_id (str): ID du livre à mettre à jour
            update_data (dict): Nouvelles données du livre
            
        Returns:
            bool: True si la mise à jour est réussie, False sinon
        """
        try:
            existing_book = self.get_book(book_id)
            if not existing_book:
                return False

            updated_book_data = {**existing_book, **update_data}
            updated_book = DBBook.from_dict(updated_book_data)
            update_dict = updated_book.to_dict()

            if '_id' in update_dict:
                del update_dict['_id']

            result = self.books_collection.update_one(
                {"_id": ObjectId(book_id)},
                {"$set": update_dict}
            )
            return result.modified_count > 0
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour du livre : {e}")
            return False

    def delete_book(self, book_id):
        """
        Supprime un livre de la base de données.
        
        Args:
            book_id (str): ID du livre à supprimer
            
        Returns:
            bool: True si la suppression est réussie, False sinon
        """
        try:
            result = self.books_collection.delete_one({"_id": ObjectId(book_id)})
            return result.deleted_count > 0
        except Exception as e:
            logging.error(f"Erreur lors de la suppression du livre : {e}")
            return False

    def get_book_by_filename(self, filename):
        """
        Récupère un livre par son nom de fichier PDF.
        
        Args:
            filename (str): Nom du fichier PDF du livre
            
        Returns:
            dict: Données du livre ou None si non trouvé
        """
        try:
            book_data = self.books_collection.find_one({"pdf_path": filename})
            if book_data:
                book_data["_id"] = str(book_data["_id"])
                return DBBook.from_dict(book_data).to_dict()
            return None
        except Exception as e:
            logging.error(f"Erreur lors de la récupération du livre par filename : {e}")
            return None

    def get_book_by_title(self, title):
        """
        Récupère un livre par son titre.
        
        Args:
            title (str): Titre du livre à rechercher
            
        Returns:
            dict: Données du livre ou None si non trouvé
        """
        try:
            book_data = self.books_collection.find_one({"title": title})
            if book_data:
                book_data["_id"] = str(book_data["_id"])
                return DBBook.from_dict(book_data).to_dict()
            return None
        except Exception as e:
            logging.error(f"Erreur lors de la récupération du livre par titre : {e}")
            return None