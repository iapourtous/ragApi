"""
Routes pour la gestion des utilisateurs.

Ce module définit toutes les routes liées à la gestion des utilisateurs,
incluant la création, la mise à jour, la suppression et la récupération
des informations utilisateur.

Routes:
    - GET /users/ : Liste tous les utilisateurs (admin)
    - POST /users/ : Crée un nouvel utilisateur (admin)
    - GET /users/<username> : Récupère un utilisateur spécifique
    - PUT /users/<username> : Met à jour un utilisateur
    - DELETE /users/<username> : Supprime un utilisateur (admin)
    - GET /users/profile : Récupère le profil de l'utilisateur connecté
    - PUT /users/profile : Met à jour le profil de l'utilisateur connecté
"""

from flask import Blueprint, jsonify, request, current_app
import logging
from app.services.user_service import UserService
from app.utils.auth_utils import token_required
from app.utils.validation_utils import validate_email, validate_password

# Création du Blueprint
user_bp = Blueprint('user', __name__)

# Initialisation du service
user_service = UserService()

@user_bp.route('/', methods=['GET'])
@token_required
def get_all_users(current_user):
    """
    Récupère la liste de tous les utilisateurs (réservé aux administrateurs).

    Args:
        current_user (dict): Informations sur l'utilisateur authentifié

    Returns:
        JSON: Liste des utilisateurs
        403: Si l'utilisateur n'est pas administrateur
        500: En cas d'erreur serveur
    """
    try:
        if current_user['role'] != 'admin':
            return jsonify({'message': 'Admin privileges required'}), 403

        users = user_service.get_all_users()
        return jsonify({'users': users}), 200
    except Exception as e:
        logging.error(f"Error getting users: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@user_bp.route('/', methods=['POST'])
@token_required
def create_user(current_user):
    """
    Crée un nouvel utilisateur (réservé aux administrateurs).

    Args:
        current_user (dict): Informations sur l'utilisateur authentifié

    Returns:
        JSON: Message de confirmation et ID de l'utilisateur créé
        400: Si les données sont invalides
        403: Si l'utilisateur n'est pas administrateur
        500: En cas d'erreur serveur
    """
    try:
        if current_user['role'] != 'admin':
            return jsonify({'message': 'Admin privileges required'}), 403

        data = request.json
        
        # Validation des données
        if not all(key in data for key in ['username', 'password', 'email']):
            return jsonify({'message': 'Missing required fields'}), 400

        # Validation du format email
        if not validate_email(data['email']):
            return jsonify({'message': 'Invalid email format'}), 400

        # Validation du mot de passe
        if not validate_password(data['password']):
            return jsonify({'message': 'Password does not meet requirements'}), 400

        # Vérification si l'utilisateur existe déjà
        if user_service.get_user_by_username(data['username']):
            return jsonify({'message': 'Username already exists'}), 400

        if user_service.get_user_by_email(data['email']):
            return jsonify({'message': 'Email already exists'}), 400

        success, message = user_service.create_user(
            username=data['username'],
            password=data['password'],
            email=data['email'],
            role=data.get('role', 'user'),
            metadata=data.get('metadata', {})
        )

        if success:
            return jsonify({'message': message}), 201
        return jsonify({'message': message}), 400

    except Exception as e:
        logging.error(f"Error creating user: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@user_bp.route('/<username>', methods=['GET'])
@token_required
def get_user(current_user, username):
    """
    Récupère les informations d'un utilisateur spécifique.

    Args:
        current_user (dict): Informations sur l'utilisateur authentifié
        username (str): Nom d'utilisateur à récupérer

    Returns:
        JSON: Informations de l'utilisateur
        403: Si l'utilisateur n'a pas les droits nécessaires
        404: Si l'utilisateur n'est pas trouvé
    """
    try:
        # Vérification des droits d'accès
        if current_user['role'] != 'admin' and current_user['username'] != username:
            return jsonify({'message': 'Unauthorized access'}), 403

        user = user_service.get_user_by_username(username)
        if not user:
            return jsonify({'message': 'User not found'}), 404

        # Filtrer les informations sensibles
        user_data = {
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'metadata': user.metadata
        }

        return jsonify(user_data), 200
    except Exception as e:
        logging.error(f"Error getting user: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@user_bp.route('/<username>', methods=['PUT'])
@token_required
def update_user(current_user, username):
    """
    Met à jour les informations d'un utilisateur.

    Args:
        current_user (dict): Informations sur l'utilisateur authentifié
        username (str): Nom d'utilisateur à mettre à jour

    Returns:
        JSON: Message de confirmation
        400: Si les données sont invalides
        403: Si l'utilisateur n'a pas les droits nécessaires
        404: Si l'utilisateur n'est pas trouvé
    """
    try:
        # Vérification des droits d'accès
        if current_user['role'] != 'admin' and current_user['username'] != username:
            return jsonify({'message': 'Unauthorized access'}), 403

        data = request.json
        
        # Validation des données si présentes
        if 'email' in data and not validate_email(data['email']):
            return jsonify({'message': 'Invalid email format'}), 400

        if 'password' in data and not validate_password(data['password']):
            return jsonify({'message': 'Password does not meet requirements'}), 400

        # Seul un admin peut changer le rôle
        if 'role' in data and current_user['role'] != 'admin':
            return jsonify({'message': 'Unauthorized to change role'}), 403

        if user_service.update(username, data):
            return jsonify({'message': 'User updated successfully'})
        return jsonify({'message': 'User not found'}), 404

    except Exception as e:
        logging.error(f"Error updating user: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@user_bp.route('/<username>', methods=['DELETE'])
@token_required
def delete_user(current_user, username):
    """
    Supprime un utilisateur (réservé aux administrateurs).

    Args:
        current_user (dict): Informations sur l'utilisateur authentifié
        username (str): Nom d'utilisateur à supprimer

    Returns:
        JSON: Message de confirmation
        403: Si l'utilisateur n'est pas administrateur
        404: Si l'utilisateur à supprimer n'est pas trouvé
    """
    try:
        if current_user['role'] != 'admin':
            return jsonify({'message': 'Admin privileges required'}), 403

        if user_service.delete(username):
            return jsonify({'message': 'User deleted successfully'})
        return jsonify({'message': 'User not found'}), 404

    except Exception as e:
        logging.error(f"Error deleting user: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@user_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """
    Récupère le profil de l'utilisateur connecté.

    Args:
        current_user (dict): Informations sur l'utilisateur authentifié

    Returns:
        JSON: Profil de l'utilisateur
        404: Si l'utilisateur n'est pas trouvé
    """
    try:
        user = user_service.get_user_by_username(current_user['username'])
        if not user:
            return jsonify({'message': 'User not found'}), 404

        profile_data = {
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'metadata': user.metadata
        }

        return jsonify(profile_data), 200
    except Exception as e:
        logging.error(f"Error getting profile: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@user_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """
    Met à jour le profil de l'utilisateur connecté.

    Args:
        current_user (dict): Informations sur l'utilisateur authentifié

    Returns:
        JSON: Message de confirmation
        400: Si les données sont invalides
        404: Si l'utilisateur n'est pas trouvé
    """
    try:
        data = request.json
        
        # Validation des données si présentes
        if 'email' in data and not validate_email(data['email']):
            return jsonify({'message': 'Invalid email format'}), 400

        if 'password' in data and not validate_password(data['password']):
            return jsonify({'message': 'Password does not meet requirements'}), 400

        # Empêcher la modification du rôle via cette route
        if 'role' in data:
            return jsonify({'message': 'Cannot change role through profile update'}), 400

        if user_service.update(current_user['username'], data):
            return jsonify({'message': 'Profile updated successfully'})
        return jsonify({'message': 'User not found'}), 404

    except Exception as e:
        logging.error(f"Error updating profile: {e}")
        return jsonify({'message': 'Internal server error'}), 500