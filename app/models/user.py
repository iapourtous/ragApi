"""
Module de gestion des utilisateurs pour l'application RAG API.

Ce module définit le modèle de données pour les utilisateurs de l'application.
Il gère l'authentification, l'autorisation et les métadonnées des utilisateurs,
implémentant le hachage sécurisé des mots de passe et des méthodes pour convertir
entre les objets utilisateurs et leur représentation pour le stockage en base de données.
"""
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    """
    Classe représentant un utilisateur du système.
    
    Cette classe gère les informations d'un utilisateur, y compris son authentification
    et ses métadonnées associées.

    Attributes:
        username (str): Nom d'utilisateur unique
        email (str): Adresse email de l'utilisateur
        password_hash (str): Hash du mot de passe de l'utilisateur
        role (str): Rôle de l'utilisateur ('user' ou 'admin')
        metadata (dict): Métadonnées additionnelles de l'utilisateur
    """

    def __init__(self, username, password, email, role="user", metadata=None, _id=None):
        """
        Initialise un nouvel utilisateur.

        Args:
            username (str): Nom d'utilisateur unique
            password (str): Mot de passe en clair (sera hashé)
            email (str): Adresse email de l'utilisateur
            role (str, optional): Rôle de l'utilisateur. Defaults to "user".
            metadata (dict, optional): Métadonnées additionnelles. Defaults to None.
            _id (str, optional): Identifiant unique de l'utilisateur. Defaults to None.
        """
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.role = role
        self.metadata = metadata or {}
        self.id = _id  # Ajout de l'attribut id

    def check_password(self, password):
        """
        Vérifie si le mot de passe fourni correspond au hash stocké.

        Args:
            password (str): Mot de passe à vérifier

        Returns:
            bool: True si le mot de passe est correct, False sinon
        """
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def create_from_db_document(doc):
        """
        Crée une instance d'utilisateur à partir d'un document de la base de données.

        Args:
            doc (dict): Document contenant les données de l'utilisateur
                Doit contenir au minimum: username, email, password_hash
                Peut contenir: role, metadata, _id

        Returns:
            User: Instance d'utilisateur créée à partir du document

        Example:
            >>> doc = {
            ...     '_id': '123456789',
            ...     'username': 'john_doe',
            ...     'email': 'john@example.com',
            ...     'password_hash': 'hashed_password',
            ...     'role': 'user',
            ...     'metadata': {'last_login': '2024-01-01'}
            ... }
            >>> user = User.create_from_db_document(doc)
        """
        user = User(doc['username'], '', doc['email'])
        user.password_hash = doc['password_hash']
        user.role = doc.get('role', 'user')
        user.metadata = doc.get('metadata', {})
        user.id = str(doc.get('_id', ''))  # Conversion de l'ID MongoDB en chaîne
        return user

    def to_dict(self):
        """
        Convertit l'instance d'utilisateur en dictionnaire.

        Cette méthode est utilisée pour la sérialisation de l'utilisateur,
        notamment pour le stockage en base de données.

        Returns:
            dict: Représentation de l'utilisateur sous forme de dictionnaire
                Contient: username, email, password_hash, role, metadata

        Example:
            >>> user = User('john_doe', 'password123', 'john@example.com')
            >>> user_dict = user.to_dict()
            >>> print(user_dict['username'])
            'john_doe'
        """
        user_dict = {
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'role': self.role,
            'metadata': self.metadata
        }
        
        # Inclure l'ID s'il existe
        if hasattr(self, 'id') and self.id:
            user_dict['_id'] = self.id
            
        return user_dict