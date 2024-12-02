import datetime
from ..mongoClient import Client
from ..models.db_blog import DBBlog
from bson import ObjectId
import logging

class BlogService:
    """
    Service gérant les opérations CRUD pour les articles de blog.
    """

    def __init__(self):
        """Initialise le service avec une connexion à la base de données."""
        self.client = Client("rag")
        self.blogs_collection = self.client.get_collection("blogs")

    def create_blog(self, blog_data):
        """
        Crée un nouvel article de blog.
        
        Args:
            blog_data (dict): Données de l'article
            
        Returns:
            str: ID de l'article créé ou None en cas d'erreur
        """
        try:
            db_blog = DBBlog(**blog_data)
            result = self.blogs_collection.insert_one(db_blog.to_dict())
            return str(result.inserted_id)
        except Exception as e:
            logging.error(f"Erreur lors de la création de l'article : {e}")
            return None

    def get_blog(self, blog_id):
        """Récupère un article par son ID."""
        try:
            blog_data = self.blogs_collection.find_one({"_id": ObjectId(blog_id)})
            if blog_data:
                blog_data["_id"] = str(blog_data["_id"])
                return blog_data
            return None
        except Exception as e:
            logging.error(f"Erreur lors de la récupération de l'article : {e}")
            return None

    def get_blog_by_pretty_url(self, pretty_url):
        """Récupère un article par son URL conviviale."""
        try:
            blog_data = self.blogs_collection.find_one({"pretty_url": pretty_url})
            if blog_data:
                blog_data["_id"] = str(blog_data["_id"])
                return blog_data
            return None
        except Exception as e:
            logging.error(f"Erreur lors de la récupération de l'article : {e}")
            return None

    def get_all_blogs(self, visible_only=True):
        """Récupère tous les articles, avec option de filtrage par visibilité."""
        try:
            query = {"is_visible": True} if visible_only else {}
            cursor = self.blogs_collection.find(query).sort("created_at", -1)
            return [{**blog, "_id": str(blog["_id"])} for blog in cursor]
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des articles : {e}")
            return []

    def get_blogs_by_category(self, category, visible_only=True):
        """Récupère les articles d'une catégorie spécifique."""
        try:
            query = {"category": category}
            if visible_only:
                query["is_visible"] = True
            cursor = self.blogs_collection.find(query).sort("created_at", -1)
            return [{**blog, "_id": str(blog["_id"])} for blog in cursor]
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des articles par catégorie : {e}")
            return []

    def update_blog(self, blog_id, update_data):
        """Met à jour un article."""
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = self.blogs_collection.update_one(
                {"_id": ObjectId(blog_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour de l'article : {e}")
            return False

    def delete_blog(self, blog_id):
        """Supprime un article."""
        try:
            result = self.blogs_collection.delete_one({"_id": ObjectId(blog_id)})
            return result.deleted_count > 0
        except Exception as e:
            logging.error(f"Erreur lors de la suppression de l'article : {e}")
            return False