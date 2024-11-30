from ..mongoClient import Client
from bson import ObjectId
import logging
from datetime import datetime
from ..models.db_contactMessage import ContactMessage

class ContactMessageService:
    """
    Service gérant les opérations CRUD pour les messages de contact.
    
    Ce service fournit une interface pour interagir avec la collection de messages
    de contact dans la base de données MongoDB. Il gère la création, la lecture,
    la mise à jour et la suppression des messages.

    Attributes:
        client: Instance de connexion à la base de données MongoDB
        messages_collection: Collection MongoDB pour les messages de contact
    """

    def __init__(self):
        """
        Initialise le service avec une connexion à la base de données.
        
        Établit une connexion à la base de données MongoDB et initialise
        la collection des messages de contact.
        """
        self.client = Client("rag")
        self.messages_collection = self.client.get_collection("contact_messages")

    def create_message(self, message_data):
        """
        Crée un nouveau message dans la base de données.

        Args:
            message_data (dict): Dictionnaire contenant les données du message avec les clés :
                - username (str): Nom de l'utilisateur
                - email (str): Email de l'utilisateur
                - message (str): Contenu du message
                - timestamp (datetime, optional): Date et heure du message
                - status (str, optional): Statut du message

        Returns:
            str: ID du message créé en cas de succès
            None: En cas d'échec de la création

        Raises:
            Exception: Si une erreur survient lors de la création du message
        """
        try:
            contact_message = ContactMessage(
                username=message_data["username"],
                email=message_data["email"],
                message=message_data["message"],
                timestamp=message_data.get("timestamp", datetime.now()),
                status=message_data.get("status", "non lu")
            )

            result = self.messages_collection.insert_one(contact_message.to_dict())
            logging.info(f"Message créé avec l'ID : {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logging.error(f"Erreur lors de la création du message : {e}")
            return None

    def get_all_messages(self):
        """
        Récupère tous les messages de contact.

        Returns:
            list: Liste de dictionnaires représentant les messages.
                  Chaque dictionnaire contient les informations suivantes :
                  - _id (str): Identifiant unique du message
                  - username (str): Nom de l'utilisateur
                  - email (str): Email de l'utilisateur
                  - message (str): Contenu du message
                  - timestamp (datetime): Date et heure du message
                  - status (str): Statut du message
            list: Liste vide en cas d'erreur

        Raises:
            Exception: Si une erreur survient lors de la récupération des messages
        """
        try:
            messages = []
            cursor = self.messages_collection.find()
            for message_data in cursor:
                message_data["_id"] = str(message_data["_id"])
                contact_message = ContactMessage.from_dict(message_data)
                messages.append(contact_message.to_dict())
            return messages
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des messages : {e}")
            return []

    def get_messages_by_status(self, status):
        """
        Récupère les messages filtrés par statut.

        Args:
            status (str): Statut des messages à récupérer (ex: "lu", "non lu")

        Returns:
            list: Liste de dictionnaires représentant les messages filtrés.
                  Chaque dictionnaire contient les mêmes informations que get_all_messages()
            list: Liste vide en cas d'erreur

        Raises:
            Exception: Si une erreur survient lors de la récupération des messages
        """
        try:
            messages = []
            cursor = self.messages_collection.find({"status": status})
            for message_data in cursor:
                message_data["_id"] = str(message_data["_id"])
                contact_message = ContactMessage.from_dict(message_data)
                messages.append(contact_message.to_dict())
            return messages
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des messages par statut : {e}")
            return []

    def delete_message(self, message_id):
        """
        Supprime un message spécifique.

        Args:
            message_id (str): Identifiant unique du message à supprimer

        Returns:
            bool: True si la suppression est réussie, False sinon

        Raises:
            Exception: Si une erreur survient lors de la suppression du message
        """
        try:
            result = self.messages_collection.delete_one({"_id": ObjectId(message_id)})
            if result.deleted_count > 0:
                logging.info(f"Message supprimé avec l'ID : {message_id}")
            else:
                logging.warning(f"Aucun message trouvé avec l'ID : {message_id}")
            return result.deleted_count > 0
        except Exception as e:
            logging.error(f"Erreur lors de la suppression du message : {e}")
            return False

    def update_message_status(self, message_id, new_status):
        """
        Met à jour le statut d'un message.

        Args:
            message_id (str): Identifiant unique du message à mettre à jour
            new_status (str): Nouveau statut à appliquer au message

        Returns:
            bool: True si la mise à jour est réussie, False sinon

        Raises:
            Exception: Si une erreur survient lors de la mise à jour du statut
        """
        try:
            result = self.messages_collection.update_one(
                {"_id": ObjectId(message_id)},
                {"$set": {"status": new_status}}
            )
            return result.modified_count > 0
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour du statut du message : {e}")
            return False