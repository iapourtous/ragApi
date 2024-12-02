# app/routes/contact_routes.py

from flask import Blueprint, jsonify, request, current_app
import logging
from app.services.contactMessageService import ContactMessageService
from app.utils.auth_utils import token_required
from app.utils.recaptcha_utils import verify_recaptcha

contact_bp = Blueprint('contact', __name__)
contact_service = ContactMessageService()

@contact_bp.route('/messages', methods=['POST'])
def create_message():
    """
    Crée un nouveau message de contact.
    
    Requiert une validation reCAPTCHA pour éviter le spam.
    
    Expected JSON:
        username (str): Nom de l'utilisateur
        email (str): Email de l'utilisateur
        message (str): Contenu du message
        captchaToken (str): Token reCAPTCHA
        
    Returns:
        JSON: Confirmation de création avec ID du message
        400: Si les données sont manquantes ou invalides
        403: Si la validation reCAPTCHA échoue
        500: En cas d'erreur serveur
    """
    try:
        data = request.json
        if not data or not all(key in data for key in ['username', 'email', 'message']):
            return jsonify({'message': 'Données manquantes'}), 400

        # Vérification reCAPTCHA
        recaptcha_token = data.get("captchaToken")
        if not recaptcha_token:
            return jsonify({"message": "reCAPTCHA token is missing"}), 400

        success, score = verify_recaptcha(recaptcha_token, "contact")
        if not success or score < 0.5:
            return jsonify({"message": "Failed reCAPTCHA validation"}), 403

        message_id = contact_service.create_message({
            'username': data['username'],
            'email': data['email'],
            'message': data['message']
        })

        if message_id:
            return jsonify({
                'message': 'Message créé avec succès',
                'message_id': message_id
            }), 201
        return jsonify({'message': 'Erreur lors de la création du message'}), 500

    except Exception as e:
        logging.error(f"Erreur lors de la création du message de contact : {e}")
        return jsonify({'message': 'Erreur serveur'}), 500

@contact_bp.route('/messages', methods=['GET'])
@token_required
def get_all_messages(current_user):
    """
    Récupère tous les messages de contact.
    Réservé aux administrateurs.
    
    Args:
        current_user (dict): Informations sur l'utilisateur authentifié
        
    Returns:
        JSON: Liste des messages
        403: Si l'utilisateur n'est pas administrateur
        500: En cas d'erreur serveur
    """
    try:
        if current_user['role'] != 'admin':
            return jsonify({'message': 'Accès non autorisé'}), 403

        messages = contact_service.get_all_messages()
        return jsonify({'messages': messages}), 200

    except Exception as e:
        logging.error(f"Erreur lors de la récupération des messages : {e}")
        return jsonify({'message': 'Erreur serveur'}), 500

@contact_bp.route('/messages/status/<status>', methods=['GET'])
@token_required
def get_messages_by_status(current_user, status):
    """
    Récupère les messages filtrés par statut.
    Réservé aux administrateurs.
    
    Args:
        current_user (dict): Informations sur l'utilisateur authentifié
        status (str): Statut des messages à récupérer
        
    Returns:
        JSON: Liste des messages filtrés
        403: Si l'utilisateur n'est pas administrateur
        500: En cas d'erreur serveur
    """
    try:
        if current_user['role'] != 'admin':
            return jsonify({'message': 'Accès non autorisé'}), 403

        messages = contact_service.get_messages_by_status(status)
        return jsonify({'messages': messages}), 200

    except Exception as e:
        logging.error(f"Erreur lors de la récupération des messages par statut : {e}")
        return jsonify({'message': 'Erreur serveur'}), 500

@contact_bp.route('/messages/<message_id>', methods=['GET'])
@token_required
def get_message(current_user, message_id):
    """
    Récupère un message spécifique par son ID.
    Réservé aux administrateurs.
    
    Args:
        current_user (dict): Informations sur l'utilisateur authentifié
        message_id (str): ID du message à récupérer
        
    Returns:
        JSON: Détails du message
        403: Si l'utilisateur n'est pas administrateur
        404: Si le message n'est pas trouvé
        500: En cas d'erreur serveur
    """
    try:
        if current_user['role'] != 'admin':
            return jsonify({'message': 'Accès non autorisé'}), 403

        message = contact_service.get_message(message_id)
        if message:
            return jsonify(message), 200
        return jsonify({'message': 'Message non trouvé'}), 404

    except Exception as e:
        logging.error(f"Erreur lors de la récupération du message : {e}")
        return jsonify({'message': 'Erreur serveur'}), 500

@contact_bp.route('/messages/<message_id>', methods=['PUT'])
@token_required
def update_message(current_user, message_id):
    """
    Met à jour un message existant.
    Réservé aux administrateurs.
    
    Args:
        current_user (dict): Informations sur l'utilisateur authentifié
        message_id (str): ID du message à mettre à jour
        
    Expected JSON:
        status (str, optional): Nouveau statut du message
        response (str, optional): Réponse au message
        
    Returns:
        JSON: Confirmation de mise à jour
        403: Si l'utilisateur n'est pas administrateur
        404: Si le message n'est pas trouvé
        500: En cas d'erreur serveur
    """
    try:
        if current_user['role'] != 'admin':
            return jsonify({'message': 'Accès non autorisé'}), 403

        data = request.json
        if contact_service.update_message(message_id, data):
            return jsonify({'message': 'Message mis à jour avec succès'})
        return jsonify({'message': 'Message non trouvé'}), 404

    except Exception as e:
        logging.error(f"Erreur lors de la mise à jour du message : {e}")
        return jsonify({'message': 'Erreur serveur'}), 500

@contact_bp.route('/messages/<message_id>', methods=['DELETE'])
@token_required
def delete_message(current_user, message_id):
    """
    Supprime un message.
    Réservé aux administrateurs.
    
    Args:
        current_user (dict): Informations sur l'utilisateur authentifié
        message_id (str): ID du message à supprimer
        
    Returns:
        JSON: Confirmation de suppression
        403: Si l'utilisateur n'est pas administrateur
        404: Si le message n'est pas trouvé
        500: En cas d'erreur serveur
    """
    try:
        if current_user['role'] != 'admin':
            return jsonify({'message': 'Accès non autorisé'}), 403

        if contact_service.delete_message(message_id):
            return jsonify({'message': 'Message supprimé avec succès'})
        return jsonify({'message': 'Message non trouvé'}), 404

    except Exception as e:
        logging.error(f"Erreur lors de la suppression du message : {e}")
        return jsonify({'message': 'Erreur serveur'}), 500

@contact_bp.route('/messages/stats', methods=['GET'])
@token_required
def get_messages_stats(current_user):
    """
    Récupère les statistiques des messages.
    Réservé aux administrateurs.
    
    Args:
        current_user (dict): Informations sur l'utilisateur authentifié
        
    Returns:
        JSON: Statistiques des messages
        403: Si l'utilisateur n'est pas administrateur
        500: En cas d'erreur serveur
    """
    try:
        if current_user['role'] != 'admin':
            return jsonify({'message': 'Accès non autorisé'}), 403

        stats = contact_service.get_messages_stats()
        return jsonify(stats), 200

    except Exception as e:
        logging.error(f"Erreur lors de la récupération des statistiques : {e}")
        return jsonify({'message': 'Erreur serveur'}), 500