"""
DTOs pour l'authentification des utilisateurs.
"""
from typing import Optional, Dict, Any, List


class LoginRequestDTO:
    """DTO pour la requête de connexion."""
    
    def __init__(self, username: str, password: str, captcha_token: Optional[str] = None):
        """
        Initialise une requête de connexion.
        
        Params:
            username: Nom d'utilisateur
            password: Mot de passe
            captcha_token: Token reCAPTCHA (optionnel)
        """
        self.username = username
        self.password = password
        self.captcha_token = captcha_token
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoginRequestDTO':
        """
        Crée un DTO à partir d'un dictionnaire.
        
        Params:
            data: Dictionnaire contenant les données
            
        Returns:
            Instance du DTO
        """
        return cls(
            username=data.get('username', ''),
            password=data.get('password', ''),
            captcha_token=data.get('captchaToken')
        )


class RegistrationRequestDTO:
    """DTO pour la requête d'inscription."""
    
    def __init__(self, username: str, password: str, email: str, 
                 captcha_token: Optional[str] = None, role: str = "user"):
        """
        Initialise une requête d'inscription.
        
        Params:
            username: Nom d'utilisateur
            password: Mot de passe
            email: Adresse email
            captcha_token: Token reCAPTCHA (optionnel)
            role: Rôle de l'utilisateur (par défaut: "user")
        """
        self.username = username
        self.password = password
        self.email = email
        self.captcha_token = captcha_token
        self.role = role
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RegistrationRequestDTO':
        """
        Crée un DTO à partir d'un dictionnaire.
        
        Params:
            data: Dictionnaire contenant les données
            
        Returns:
            Instance du DTO
        """
        return cls(
            username=data.get('username', ''),
            password=data.get('password', ''),
            email=data.get('email', ''),
            captcha_token=data.get('captchaToken'),
            role=data.get('role', 'user')
        )


class AuthResponseDTO:
    """DTO pour la réponse d'authentification."""
    
    def __init__(self, token: str, role: str, username: str, user_id: str):
        """
        Initialise une réponse d'authentification.
        
        Params:
            token: Token JWT
            role: Rôle de l'utilisateur
            username: Nom d'utilisateur
            user_id: Identifiant de l'utilisateur
        """
        self.token = token
        self.role = role
        self.username = username
        self.user_id = user_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le DTO en dictionnaire.
        
        Returns:
            Dictionnaire représentant le DTO
        """
        return {
            'token': self.token,
            'role': self.role,
            'username': self.username,
            'userId': self.user_id
        }