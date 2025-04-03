"""
Utilitaires d'authentification pour l'application RAG API.

Ce module fournit des fonctions et décorateurs pour gérer l'authentification
des utilisateurs via JWT (JSON Web Tokens). Il implémente notamment un décorateur
qui vérifie la validité du token dans les en-têtes de la requête.
"""
from functools import wraps
from flask import jsonify, request, current_app
import jwt

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = {
                'username': data['username'],
                'role': data['role'],
                'id': data.get('id', '')  # Inclure l'ID utilisateur s'il existe dans le token
            }
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated