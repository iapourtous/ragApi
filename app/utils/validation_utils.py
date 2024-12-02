import re

def validate_email(email):
    """
    Valide le format d'une adresse email.

    Args:
        email (str): Adresse email à valider

    Returns:
        bool: True si l'email est valide, False sinon
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password):
    """
    Valide la force d'un mot de passe.
    
    Règles :
    - Au moins 8 caractères
    - Au moins une lettre majuscule
    - Au moins une lettre minuscule
    - Au moins un chiffre
    - Au moins un caractère spécial

    Args:
        password (str): Mot de passe à valider

    Returns:
        bool: True si le mot de passe est valide, False sinon
    """
    if len(password) < 8:
        return False
    
    if not re.search(r'[A-Z]', password):
        return False
        
    if not re.search(r'[a-z]', password):
        return False
        
    if not re.search(r'[0-9]', password):
        return False
        
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
        
    return True