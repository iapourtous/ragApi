"""
Module définissant le modèle de données pour les messages de contact.

Ce module fournit une classe ContactMessage qui représente un message de contact
dans le système, avec des méthodes pour la sérialisation et la désérialisation
des données.
"""

from datetime import datetime

class ContactMessage:
    """
    Classe représentant un message de contact dans le système.

    Cette classe gère la structure et la validation des données d'un message
    de contact, ainsi que sa conversion depuis et vers un format dictionnaire
    pour le stockage en base de données.

    Attributes:
        _id (str): Identifiant unique du message en base de données
        username (str): Nom de l'utilisateur ayant envoyé le message
        email (str): Adresse email de l'utilisateur
        message (str): Contenu du message
        timestamp (datetime): Date et heure d'envoi du message
        status (str): État actuel du message (par défaut: "non lu")
    """

    def __init__(self, username, email, message, timestamp=None, status="non lu", _id=None):
        """
        Initialise une nouvelle instance de ContactMessage.

        Args:
            username (str): Nom de l'utilisateur ayant envoyé le message
            email (str): Adresse email de l'utilisateur
            message (str): Contenu du message
            timestamp (datetime, optional): Date et heure d'envoi du message.
                Si non fourni, utilise l'heure actuelle.
            status (str, optional): État du message. Par défaut "non lu".
            _id (str, optional): Identifiant unique du message.
                Généralement fourni par la base de données.

        Example:
            >>> message = ContactMessage(
            ...     username="John Doe",
            ...     email="john@example.com",
            ...     message="Hello, I need help!"
            ... )
        """
        self._id = _id
        self.username = username
        self.email = email
        self.message = message
        self.timestamp = timestamp or datetime.now()
        self.status = status

    @staticmethod
    def from_dict(data):
        """
        Crée une instance de ContactMessage à partir d'un dictionnaire.

        Cette méthode statique permet de créer une instance de ContactMessage
        à partir de données structurées, typiquement issues de la base de données.

        Args:
            data (dict): Dictionnaire contenant les données du message.
                Doit contenir les clés : username, email, message.
                Peut contenir : _id, timestamp, status.

        Returns:
            ContactMessage: Une nouvelle instance de ContactMessage.

        Example:
            >>> data = {
            ...     "username": "John Doe",
            ...     "email": "john@example.com",
            ...     "message": "Hello!",
            ...     "status": "lu"
            ... }
            >>> message = ContactMessage.from_dict(data)
        """
        return ContactMessage(
            _id=data.get('_id'),
            username=data.get('username'),
            email=data.get('email'),
            message=data.get('message'),
            timestamp=data.get('timestamp'),
            status=data.get('status', 'non lu')
        )

    def to_dict(self):
        """
        Convertit l'instance en dictionnaire.

        Cette méthode sérialise l'instance de ContactMessage en un dictionnaire,
        format adapté pour le stockage en base de données ou la transmission API.

        Returns:
            dict: Dictionnaire contenant toutes les données du message.
                Les clés sont : username, email, message, timestamp, status.
                Si _id existe, il est également inclus.

        Example:
            >>> message = ContactMessage("John", "john@example.com", "Hello")
            >>> data = message.to_dict()
            >>> print(data['username'])
            'John'
        """
        data = {
            'username': self.username,
            'email': self.email,
            'message': self.message,
            'timestamp': self.timestamp,
            'status': self.status
        }
        if self._id:
            data['_id'] = self._id
        return data

    def __str__(self):
        """
        Retourne une représentation string de l'instance.

        Returns:
            str: Représentation lisible du message de contact.
        """
        return f"Message de {self.username} ({self.email}) - Status: {self.status}"

    def __repr__(self):
        """
        Retourne une représentation détaillée de l'instance.

        Returns:
            str: Représentation technique du message de contact.
        """
        return f"ContactMessage(username='{self.username}', email='{self.email}', status='{self.status}', _id={self._id})"