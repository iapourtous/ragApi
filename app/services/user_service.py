from ..mongoClient import Client
from ..models.user import User
from werkzeug.security import generate_password_hash
import logging

class UserService:
    """
    Service gérant les opérations liées aux utilisateurs dans la base de données.
    
    Ce service fournit des méthodes pour créer, lire, mettre à jour et supprimer
    des utilisateurs, ainsi que pour gérer l'authentification.
    """

    def __init__(self):
        """
        Initialise le service utilisateur avec une connexion à la base de données.
        """
        self.client = Client("rag")
        self.users_collection = self.client.get_collection("users")

    def create_default_user(self):
        """
        Crée l'utilisateur administrateur par défaut si aucun utilisateur n'existe.
        
        Cette méthode est généralement appelée lors de l'initialisation de l'application
        pour s'assurer qu'il existe au moins un compte administrateur.
        
        Returns:
            None
        """
        if self.users_collection.count_documents({}) == 0:
            default_user = User(
                username="admin",
                email="admin@localhost.com",
                password="npqeacqtnss",
                role="admin"
            )
            self.users_collection.insert_one(default_user.to_dict())
            logging.info("Utilisateur par défaut créé")

    def get_user_by_email(self, email):
        """
        Récupère un utilisateur par son adresse email.
        
        Args:
            email (str): L'adresse email de l'utilisateur recherché
            
        Returns:
            User: L'instance de l'utilisateur trouvé ou None si non trouvé
        """
        user_doc = self.users_collection.find_one({"email": email})
        if user_doc:
            return User.create_from_db_document(user_doc)
        return None

    def get_user_by_username(self, username):
        """
        Récupère un utilisateur par son nom d'utilisateur.
        
        Args:
            username (str): Le nom d'utilisateur recherché
            
        Returns:
            User: L'instance de l'utilisateur trouvé ou None si non trouvé
        """
        user_doc = self.users_collection.find_one({"username": username})
        if user_doc:
            return User.create_from_db_document(user_doc)
        return None

    def create_user(self, username, password, email, role="user", metadata=None):
        """
        Crée un nouvel utilisateur dans la base de données.
        
        Args:
            username (str): Nom d'utilisateur
            password (str): Mot de passe en clair
            email (str): Adresse email
            role (str, optional): Rôle de l'utilisateur. Defaults to "user".
            metadata (dict, optional): Métadonnées supplémentaires. Defaults to None.
            
        Returns:
            tuple: (success: bool, message: str)
                - success: True si la création est réussie, False sinon
                - message: Message décrivant le résultat de l'opération
        """
        if self.get_user_by_username(username):
            return False, "Username already exists"
        if self.get_user_by_email(email):
            return False, "Email already exists"

        new_user = User(username, password, email, role, metadata)
        self.users_collection.insert_one(new_user.to_dict())
        return True, "User created successfully"

    def update_user(self, username, updates):
        """
        Met à jour les informations d'un utilisateur.
        
        Args:
            username (str): Nom d'utilisateur de l'utilisateur à mettre à jour
            updates (dict): Dictionnaire contenant les champs à mettre à jour
            
        Returns:
            bool: True si la mise à jour est réussie, False sinon
        """
        if 'password' in updates:
            updates['password_hash'] = generate_password_hash(updates.pop('password'))
        result = self.users_collection.update_one(
            {"username": username},
            {"$set": updates}
        )
        return result.modified_count > 0

    def delete_user(self, username):
        """
        Supprime un utilisateur de la base de données.
        
        Args:
            username (str): Nom d'utilisateur de l'utilisateur à supprimer
            
        Returns:
            bool: True si la suppression est réussie, False sinon
        """
        result = self.users_collection.delete_one({"username": username})
        return result.deleted_count > 0