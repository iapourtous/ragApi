from ..mongoClient import Client
from ..models.db_book import DBBook
from ..utils.book_embedding_utils import (
    generate_description_embedding, should_update_embedding, 
    search_books_by_embedding, calculate_embedding_stats
)
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
            book_id = str(result.inserted_id)
            logging.info(f"Livre créé avec l'ID : {book_id}")
            
            # Générer l'embedding de la description si présente
            if book_data.get('description'):
                self._update_book_embedding(book_id, book_data['description'])
            
            return book_id
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
                # Assurer que category et subcategory existent
                if 'category' not in book_data:
                    book_data['category'] = None
                if 'subcategory' not in book_data:
                    book_data['subcategory'] = None
                return DBBook.from_dict(book_data).to_dict()
            return None
        except Exception as e:
            logging.error(f"Erreur lors de la récupération du livre par ID : {e}")
            return None

    def get_all_books(self):
        """
        Récupère tous les livres de la base de données.
                
        Returns:
            list: Liste de tous les livres
        """
        try:
            books = []
            cursor = self.books_collection.find()

            for book_data in cursor:
                book_data["_id"] = str(book_data["_id"])
                # Assurer que category et subcategory existent
                if 'category' not in book_data:
                    book_data['category'] = None
                if 'subcategory' not in book_data:
                    book_data['subcategory'] = None
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
            
            # Mettre à jour l'embedding si la description a changé
            if 'description' in update_data:
                old_description = existing_book.get('description', '')
                new_description = update_data.get('description', '')
                
                # Vérifier si la description a réellement changé
                if old_description != new_description:
                    if new_description and new_description.strip():
                        # Nouvelle description non-vide : générer l'embedding
                        self._update_book_embedding(book_id, new_description)
                        logging.info(f"Embedding mis à jour pour le livre {book_id} (description modifiée)")
                    else:
                        # Description supprimée ou vide : supprimer l'embedding
                        self._clear_book_embedding(book_id)
                        logging.info(f"Embedding supprimé pour le livre {book_id} (description supprimée)")
            
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
                # Assurer que category et subcategory existent
                if 'category' not in book_data:
                    book_data['category'] = None
                if 'subcategory' not in book_data:
                    book_data['subcategory'] = None
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
                # Assurer que category et subcategory existent
                if 'category' not in book_data:
                    book_data['category'] = None
                if 'subcategory' not in book_data:
                    book_data['subcategory'] = None
                return DBBook.from_dict(book_data).to_dict()
            return None
        except Exception as e:
            logging.error(f"Erreur lors de la récupération du livre par titre : {e}")
            return None

    def _update_book_embedding(self, book_id, description):
        """
        Met à jour l'embedding d'un livre basé sur sa description.
        
        Args:
            book_id (str): ID du livre
            description (str): Description du livre
        """
        try:
            from flask import current_app
            
            if not current_app or not hasattr(current_app, 'model'):
                logging.warning("Modèle d'embedding non disponible, embedding ignoré")
                return
            
            embedding_data, model_name, timestamp = generate_description_embedding(
                description, current_app.model
            )
            
            if embedding_data:
                update_result = self.books_collection.update_one(
                    {"_id": ObjectId(book_id)},
                    {"$set": {
                        "description_embedding": embedding_data,
                        "description_embedding_model": model_name,
                        "description_embedding_date": timestamp
                    }}
                )
                if update_result.modified_count > 0:
                    logging.info(f"Embedding mis à jour pour le livre {book_id}")
                else:
                    logging.warning(f"Échec de la mise à jour de l'embedding pour le livre {book_id}")
            
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour de l'embedding : {e}")

    def _clear_book_embedding(self, book_id):
        """
        Supprime l'embedding d'un livre (quand la description est supprimée).
        
        Args:
            book_id (str): ID du livre
        """
        try:
            update_result = self.books_collection.update_one(
                {"_id": ObjectId(book_id)},
                {"$unset": {
                    "description_embedding": "",
                    "description_embedding_model": "",
                    "description_embedding_date": ""
                }}
            )
            if update_result.modified_count > 0:
                logging.info(f"Embedding supprimé pour le livre {book_id}")
            else:
                logging.warning(f"Échec de la suppression de l'embedding pour le livre {book_id}")
                
        except Exception as e:
            logging.error(f"Erreur lors de la suppression de l'embedding : {e}")

    def search_books_by_description(self, query, top_k=5, threshold=0.5):
        """
        Recherche des livres par similarité sémantique de description.
        
        Args:
            query (str): Requête de recherche
            top_k (int): Nombre maximum de résultats à retourner
            threshold (float): Seuil de similarité minimum (0-1)
            
        Returns:
            list: Liste des livres trouvés avec leurs scores de similarité
        """
        try:
            from flask import current_app
            
            if not current_app or not hasattr(current_app, 'model'):
                logging.error("Modèle d'embedding non disponible pour la recherche")
                return []
            
            # Récupérer tous les livres avec leurs embeddings
            all_books = self.get_all_books()
            
            # Effectuer la recherche
            results = search_books_by_embedding(
                query, all_books, current_app.model, top_k, threshold
            )
            
            return results
            
        except Exception as e:
            logging.error(f"Erreur lors de la recherche par description : {e}")
            return []

    def get_embedding_stats(self):
        """
        Récupère les statistiques des embeddings pour tous les livres.
        
        Returns:
            dict: Statistiques des embeddings
        """
        try:
            all_books = self.get_all_books()
            return calculate_embedding_stats(all_books)
        except Exception as e:
            logging.error(f"Erreur lors du calcul des statistiques : {e}")
            return {}

    def migrate_embeddings(self, batch_size=10):
        """
        Migre les embeddings pour tous les livres qui en ont besoin.
        
        Args:
            batch_size (int): Nombre de livres à traiter par lot
            
        Returns:
            dict: Résumé de la migration
        """
        try:
            from flask import current_app
            
            if not current_app or not hasattr(current_app, 'model'):
                logging.error("Modèle d'embedding non disponible pour la migration")
                return {"error": "Modèle non disponible"}
            
            # Récupérer les livres qui ont besoin d'un embedding
            books_needing_embedding = list(self.books_collection.find({
                "$and": [
                    {"description": {"$exists": True, "$ne": None, "$ne": ""}},
                    {"$or": [
                        {"description_embedding": {"$exists": False}},
                        {"description_embedding": None},
                        {"description_embedding": []}
                    ]}
                ]
            }))
            
            # Debug: regarder tous les livres avec description
            all_books_with_desc = list(self.books_collection.find({"description": {"$exists": True, "$ne": None, "$ne": ""}}))
            logging.info(f"Total livres avec description: {len(all_books_with_desc)}")
            for book in all_books_with_desc[:3]:  # Log 3 premiers
                has_embedding = book.get('description_embedding') is not None
                logging.info(f"Livre {book.get('_id')}: has_embedding={has_embedding}")
            
            total_books = len(books_needing_embedding)
            processed = 0
            errors = 0
            
            logging.info(f"Début de la migration de {total_books} livres")
            
            for i in range(0, total_books, batch_size):
                batch = books_needing_embedding[i:i + batch_size]
                
                for book in batch:
                    try:
                        book_id = str(book['_id'])
                        description = book.get('description', '')
                        
                        if description and description.strip():
                            self._update_book_embedding(book_id, description)
                            processed += 1
                        
                    except Exception as e:
                        logging.error(f"Erreur lors du traitement du livre {book.get('_id')}: {e}")
                        errors += 1
                
                # Log de progression
                progress = min(i + batch_size, total_books)
                logging.info(f"Migration: {progress}/{total_books} livres traités")
            
            result = {
                "total_books": total_books,
                "processed": processed,
                "errors": errors,
                "success_rate": (processed / max(total_books, 1)) * 100
            }
            
            logging.info(f"Migration terminée: {result}")
            return result
            
        except Exception as e:
            logging.error(f"Erreur lors de la migration des embeddings : {e}")
            return {"error": str(e)}