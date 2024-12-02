import logging
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timedelta
import jwt
from app.services import UserService
from app.utils.auth_utils import token_required
from app.utils.recaptcha_utils import verify_recaptcha

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
    auth = request.json
    
        # Vérification reCAPTCHA
    recaptcha_token = auth.get("captchaToken")
    if not recaptcha_token:
        return jsonify({"message": "reCAPTCHA token is missing"}), 400
    
    success, score = verify_recaptcha(recaptcha_token,"login")
    logging.info(f"Srore:{score}")
    if not success or score < 0.5:
        return jsonify({"message": "Failed reCAPTCHA validation"}), 403
        
    
    if not auth or not auth.get('username') or not auth.get('password'):
        return jsonify({'message': 'Could not verify'}), 401

    user = user_service.get_user_by_username(auth.get('username'))
    if not user:
        return jsonify({'message': 'User not found'}), 401

    if user.check_password(auth.get('password')):
        token = jwt.encode({
            'username': user.username,
            'role': user.role,
            'exp': datetime.utcnow() + timedelta(minutes=30)
        }, current_app.config['SECRET_KEY'], algorithm="HS256")

        return jsonify({
            'token': token.decode('UTF-8') if isinstance(token, bytes) else token,
            'role': user.role
        })

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
        data = request.json
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        recaptcha_token = data.get('captchaToken')
        
        if not recaptcha_token:
            return jsonify({"message": "reCAPTCHA token is missing"}), 400

        # Validation reCAPTCHA
        success, score = verify_recaptcha(recaptcha_token,"signup")
        if not success or score < 0.8:
            return jsonify({"message": "Failed reCAPTCHA validation"}), 403           

        # Vérifier si l'utilisateur existe déjà
        if user_service.get_user_by_username(username):
            return jsonify({'message': 'Username already exists'}), 400
            
        if user_service.get_user_by_email(email):
            return jsonify({'message': 'Email already exists'}), 400

        # Créer le nouvel utilisateur
        success, message = user_service.create_user(
            username=username,
            password=password,
            email=email,
            role='user'  # Par défaut, les nouveaux utilisateurs ont le rôle 'user'
        )

        if success:
            # Générer un token pour le nouvel utilisateur
            token = jwt.encode({
                'username': username,
                'role': 'user',
                'exp': datetime.utcnow() + timedelta(minutes=30)
            }, current_app.config['SECRET_KEY'], algorithm="HS256")

            return jsonify({
                'message': 'User created successfully',
                'token': token
            }), 201
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
            'exp': datetime.utcnow() + timedelta(minutes=30)
        }, current_app.config['SECRET_KEY'], algorithm="HS256")

        # Préparer la réponse
        response_data = {
            'message': 'Token is valid',
            'token': new_token.decode('UTF-8') if isinstance(new_token, bytes) else new_token,
            'user': {
                'username': current_user['username'],
                'role': current_user['role']
            }
        }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({'message': 'Error refreshing token', 'error': str(e)}), 500