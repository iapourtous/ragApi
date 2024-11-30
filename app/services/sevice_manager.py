from app.services.queryData_service import QueryDataService
from app.services.book_service import BookService
from app.services.user_service import UserService

class ServiceManager:
    """
    Gestionnaire centralisé des services de l'application.
    
    Cette classe implémente le pattern Singleton pour assurer une instance unique
    des services à travers l'application. Elle gère l'initialisation et l'accès
    aux différents services (livre, utilisateur, requête).

    Attributes:
        _instance (ServiceManager): Instance unique du gestionnaire de services
        config (dict): Configuration de l'application
        book_service (BookService): Service de gestion des livres
        user_service (UserService): Service de gestion des utilisateurs
        query_service (QueryDataService): Service de gestion des requêtes
    """

    _instance = None

    def __new__(cls, config=None):
        """
        Crée ou retourne l'instance unique du gestionnaire de services.

        Args:
            config (dict, optional): Configuration de l'application. Defaults to None.

        Returns:
            ServiceManager: Instance unique du gestionnaire de services
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialize(config)
        return cls._instance

    def initialize(self, config=None):
        """
        Initialise les services avec la configuration fournie.

        Cette méthode est appelée une seule fois lors de la création de l'instance
        et configure tous les services nécessaires.

        Args:
            config (dict, optional): Configuration de l'application. Defaults to None.
        """
        self.config = config or {}
        self.book_service = BookService()
        self.user_service = UserService()
        self.query_service = QueryDataService()

    def cleanup(self):
        """
        Nettoie les ressources utilisées par les services.

        Cette méthode doit être appelée lors de l'arrêt de l'application pour
        assurer une fermeture propre des connexions et des ressources.
        """
        # Fermeture propre des connexions, etc.
        pass