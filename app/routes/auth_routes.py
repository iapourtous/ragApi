import logging
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timedelta
import jwt
from app.services import UserService
from app.utils.auth_utils import token_required
from app.utils.recaptcha_utils import verify_recaptcha
from app.dto.auth_dto import LoginRequestDTO, RegistrationRequestDTO, AuthResponseDTO

auth_bp = Blueprint('auth', __name__)
user_service = UserService()

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Gère l'authentification des utilisateurs.
    
    Vérifie les identifiants fournis et le token reCAPTCHA.
    Génère un token JWT en cas de succès.
    
    Returns:
        JSON: Token JWT et rôle de l'utilisateur en cas de succès
        401: Si les identifiants sont invalides
        400: Si le token reCAPTCHA est manquant
        403: Si la validation reCAPTCHA échoue
    """        
    # Conversion de la requête JSON en DTO
    login_request = LoginRequestDTO.from_dict(request.json)
    
    # Validation des données
    if not login_request.username or not login_request.password:
        return jsonify({'message': 'Username and password are required'}), 401
    
    # Vérification reCAPTCHA
    if not login_request.captcha_token:
        return jsonify({"message": "reCAPTCHA token is missing"}), 400
    
    success, score = verify_recaptcha(login_request.captcha_token, "login")
    logging.info(f"Score: {score}")
    if not success or score < 0.5:
        return jsonify({"message": "Failed reCAPTCHA validation"}), 403
    
    # Récupération de l'utilisateur
    user = user_service.get_user_by_username(login_request.username)
    if not user:
        return jsonify({'message': 'User not found'}), 401

    # Vérification du mot de passe
    if user.check_password(login_request.password):
        # Vérifier si l'ID existe et l'utiliser dans le token
        user_id = str(user.id) if hasattr(user, 'id') else ''
        
        token = jwt.encode({
            'username': user.username,
            'role': user.role,
            'id': user_id,
            'exp': datetime.utcnow() + timedelta(minutes=30)
        }, current_app.config['SECRET_KEY'], algorithm="HS256")

        # Création du DTO de réponse
        auth_response = AuthResponseDTO(
            token=token.decode('UTF-8') if isinstance(token, bytes) else token,
            role=user.role,
            username=user.username,
            user_id=user_id
        )

        return jsonify(auth_response.to_dict())

    return jsonify({'message': 'Invalid credentials'}), 401
    
@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Gère l'inscription des nouveaux utilisateurs.
    
    Vérifie le token reCAPTCHA et crée un nouvel utilisateur.
    
    Returns:
        JSON: Token JWT et message de confirmation
        400: Si les données sont invalides ou l'utilisateur existe déjà
        403: Si la validation reCAPTCHA échoue
        500: En cas d'erreur serveur
    """
    try: 
        # Conversion de la requête JSON en DTO
        registration_request = RegistrationRequestDTO.from_dict(request.json)
        
        # Validation des données
        if not registration_request.username or not registration_request.password or not registration_request.email:
            return jsonify({'message': 'Username, password and email are required'}), 400
        
        # Vérification reCAPTCHA
        if not registration_request.captcha_token:
            return jsonify({"message": "reCAPTCHA token is missing"}), 400

        # Validation reCAPTCHA
        success, score = verify_recaptcha(registration_request.captcha_token, "signup")
        if not success or score < 0.8:
            return jsonify({"message": "Failed reCAPTCHA validation"}), 403           

        # Vérifier si l'utilisateur existe déjà
        if user_service.get_user_by_username(registration_request.username):
            return jsonify({'message': 'Username already exists'}), 400
            
        if user_service.get_user_by_email(registration_request.email):
            return jsonify({'message': 'Email already exists'}), 400

        # Créer le nouvel utilisateur
        success, message, user_id = user_service.create_user(
            username=registration_request.username,
            password=registration_request.password,
            email=registration_request.email,
            role=registration_request.role
        )

        if success:
            # Générer un token pour le nouvel utilisateur
            token = jwt.encode({
                'username': registration_request.username,
                'role': registration_request.role,
                'id': str(user_id),
                'exp': datetime.utcnow() + timedelta(minutes=30)
            }, current_app.config['SECRET_KEY'], algorithm="HS256")

            # Création du DTO de réponse
            auth_response = AuthResponseDTO(
                token=token.decode('UTF-8') if isinstance(token, bytes) else token,
                role=registration_request.role,
                username=registration_request.username,
                user_id=str(user_id)
            )

            return jsonify(auth_response.to_dict()), 201
        else:
            return jsonify({'message': message}), 400

    except Exception as e:
        logging.error(f"Error during registration: {e}")
        return jsonify({'message': 'An error occurred during registration'}), 500
    
@auth_bp.route('/protected', methods=['GET'])
@token_required
def protected(current_user):
    """
    Route protégée pour vérifier et renouveler le token JWT.
    
    Args:
        current_user (dict): Informations de l'utilisateur courant (injecté par token_required)
        
    Returns:
        JSON: Nouveau token JWT et informations utilisateur
    """
    try:
        # Générer un nouveau token
        new_token = jwt.encode({
            'username': current_user['username'],
            'role': current_user['role'],
            'id': current_user.get('id', ''),
            'exp': datetime.utcnow() + timedelta(minutes=30)
        }, current_app.config['SECRET_KEY'], algorithm="HS256")

        # Création du DTO de réponse
        auth_response = AuthResponseDTO(
            token=new_token.decode('UTF-8') if isinstance(new_token, bytes) else new_token,
            role=current_user['role'],
            username=current_user['username'],
            user_id=current_user.get('id', '')
        )

        return jsonify(auth_response.to_dict()), 200

    except Exception as e:
        return jsonify({'message': 'Error refreshing token', 'error': str(e)}), 500