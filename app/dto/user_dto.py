"""
DTOs pour la gestion des utilisateurs.
"""
from typing import Optional, Dict, Any, List


class UserDTO:
    """DTO de base pour un utilisateur."""
    
    def __init__(self, id: str, username: str, email: str, role: str,
                 created_at: Optional[str] = None, updated_at: Optional[str] = None):
        """
        Initialise un DTO d'utilisateur.
        
        Params:
            id: Identifiant de l'utilisateur
            username: Nom d'utilisateur
            email: Adresse email
            role: Rôle de l'utilisateur
            created_at: Date de création (optionnel)
            updated_at: Date de mise à jour (optionnel)
        """
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.created_at = created_at
        self.updated_at = updated_at
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserDTO':
        """
        Crée un DTO à partir d'un dictionnaire.
        
        Params:
            data: Dictionnaire contenant les données
            
        Returns:
            Instance du DTO
        """
        return cls(
            id=data.get('_id', ''),
            username=data.get('username', ''),
            email=data.get('email', ''),
            role=data.get('role', 'user'),
            created_at=data.get('createdAt'),
            updated_at=data.get('updatedAt')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le DTO en dictionnaire.
        
        Returns:
            Dictionnaire représentant le DTO
        """
        result = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role
        }
        
        if self.created_at:
            result['createdAt'] = self.created_at
        if self.updated_at:
            result['updatedAt'] = self.updated_at
            
        return result


class UserCreateDTO:
    """DTO pour la création d'un utilisateur."""
    
    def __init__(self, username: str, email: str, password: str, role: str = 'user'):
        """
        Initialise un DTO de création d'utilisateur.
        
        Params:
            username: Nom d'utilisateur
            email: Adresse email
            password: Mot de passe
            role: Rôle de l'utilisateur (par défaut: "user")
        """
        self.username = username
        self.email = email
        self.password = password
        self.role = role
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserCreateDTO':
        """
        Crée un DTO à partir d'un dictionnaire.
        
        Params:
            data: Dictionnaire contenant les données
            
        Returns:
            Instance du DTO
        """
        return cls(
            username=data.get('username', ''),
            email=data.get('email', ''),
            password=data.get('password', ''),
            role=data.get('role', 'user')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le DTO en dictionnaire.
        
        Returns:
            Dictionnaire représentant le DTO
        """
        return {
            'username': self.username,
            'email': self.email,
            'password': self.password,
            'role': self.role
        }


class UserUpdateDTO:
    """DTO pour la mise à jour d'un utilisateur."""
    
    def __init__(self, username: Optional[str] = None, 
                 email: Optional[str] = None,
                 password: Optional[str] = None,
                 role: Optional[str] = None):
        """
        Initialise un DTO de mise à jour d'utilisateur.
        
        Params:
            username: Nom d'utilisateur (optionnel)
            email: Adresse email (optionnel)
            password: Mot de passe (optionnel)
            role: Rôle de l'utilisateur (optionnel)
        """
        self.username = username
        self.email = email
        self.password = password
        self.role = role
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserUpdateDTO':
        """
        Crée un DTO à partir d'un dictionnaire.
        
        Params:
            data: Dictionnaire contenant les données
            
        Returns:
            Instance du DTO
        """
        return cls(
            username=data.get('username'),
            email=data.get('email'),
            password=data.get('password'),
            role=data.get('role')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le DTO en dictionnaire, en excluant les valeurs None.
        
        Returns:
            Dictionnaire représentant le DTO
        """
        result = {}
        if self.username is not None:
            result['username'] = self.username
        if self.email is not None:
            result['email'] = self.email
        if self.password is not None:
            result['password'] = self.password
        if self.role is not None:
            result['role'] = self.role
        return result


class UserResponseDTO:
    """DTO pour la réponse d'un utilisateur (sans données sensibles)."""
    
    def __init__(self, id: str, username: str, email: str, role: str,
                 created_at: Optional[str] = None, updated_at: Optional[str] = None):
        """
        Initialise un DTO de réponse d'utilisateur.
        
        Params:
            id: Identifiant de l'utilisateur
            username: Nom d'utilisateur
            email: Adresse email
            role: Rôle de l'utilisateur
            created_at: Date de création (optionnel)
            updated_at: Date de mise à jour (optionnel)
        """
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.created_at = created_at
        self.updated_at = updated_at
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserResponseDTO':
        """
        Crée un DTO à partir d'un dictionnaire.
        
        Params:
            data: Dictionnaire contenant les données
            
        Returns:
            Instance du DTO
        """
        return cls(
            id=data.get('_id', ''),
            username=data.get('username', ''),
            email=data.get('email', ''),
            role=data.get('role', 'user'),
            created_at=data.get('createdAt'),
            updated_at=data.get('updatedAt')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le DTO en dictionnaire.
        
        Returns:
            Dictionnaire représentant le DTO
        """
        result = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role
        }
        
        if self.created_at:
            result['createdAt'] = self.created_at
        if self.updated_at:
            result['updatedAt'] = self.updated_at
            
        return result


class UserListResponseDTO:
    """DTO pour la réponse de liste d'utilisateurs."""
    
    def __init__(self, users: List[UserResponseDTO], total: int, page: int, per_page: int):
        """
        Initialise une réponse de liste d'utilisateurs.
        
        Params:
            users: Liste des utilisateurs
            total: Nombre total d'utilisateurs
            page: Page actuelle
            per_page: Nombre d'utilisateurs par page
        """
        self.users = users
        self.total = total
        self.page = page
        self.per_page = per_page
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le DTO en dictionnaire.
        
        Returns:
            Dictionnaire représentant le DTO
        """
        return {
            'users': [user.to_dict() for user in self.users],
            'total': self.total,
            'page': self.page,
            'perPage': self.per_page
        }