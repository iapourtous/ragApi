"""
Module de service pour la gestion des utilisateurs dans l'application RAG API.

Ce module implémente la couche de service qui permet d'interagir avec la collection
d'utilisateurs dans la base de données MongoDB. Il fournit des fonctionnalités pour
la création, la recherche, la mise à jour et la suppression d'utilisateurs, ainsi
que pour l'initialisation d'un compte administrateur par défaut au démarrage de
l'application.
"""
from ..mongoClient import Client
from ..models.user import User
from ..dto.user_dto import UserCreateDTO, UserUpdateDTO, UserResponseDTO
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
            tuple: (success: bool, message: str, user_id: str)
                - success: True si la création est réussie, False sinon
                - message: Message décrivant le résultat de l'opération
                - user_id: ID de l'utilisateur créé ou None si échec
        """
        if self.get_user_by_username(username):
            return False, "Username already exists", None
        if self.get_user_by_email(email):
            return False, "Email already exists", None

        new_user = User(username, password, email, role, metadata)
        user_dict = new_user.to_dict()
        result = self.users_collection.insert_one(user_dict)
        user_id = str(result.inserted_id)
        return True, "User created successfully", user_id

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
        
    def get_user_response_dto(self, user_or_id):
        """
        Récupère un utilisateur et le convertit en DTO de réponse.
        
        Args:
            user_or_id: L'utilisateur (User) ou son ID (str)
            
        Returns:
            UserResponseDTO: Le DTO de réponse pour l'utilisateur ou None si non trouvé
        """
        user = None
        if isinstance(user_or_id, User):
            user = user_or_id
        elif isinstance(user_or_id, str):
            user_doc = self.users_collection.find_one({"_id": user_or_id})
            if user_doc:
                user = User.create_from_db_document(user_doc)
                
        if user:
            return UserResponseDTO(
                id=str(user.id),
                username=user.username,
                email=user.email,
                role=user.role,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
        return None
        
    def create_user_from_dto(self, user_dto):
        """
        Crée un utilisateur à partir d'un DTO.
        
        Args:
            user_dto (UserCreateDTO): DTO contenant les informations de l'utilisateur
            
        Returns:
            tuple: (success: bool, message: str, user_id: str)
        """
        return self.create_user(
            username=user_dto.username,
            password=user_dto.password,
            email=user_dto.email,
            role=user_dto.role
        )
        
    def update_user_from_dto(self, username, user_dto):
        """
        Met à jour un utilisateur à partir d'un DTO.
        
        Args:
            username (str): Nom d'utilisateur de l'utilisateur à mettre à jour
            user_dto (UserUpdateDTO): DTO contenant les informations à mettre à jour
            
        Returns:
            bool: True si la mise à jour est réussie, False sinon
        """
        updates = user_dto.to_dict()
        return self.update_user(username, updates)