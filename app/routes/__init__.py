"""
Module d'initialisation des routes pour l'application RAG API.

Ce module centralise l'enregistrement de toutes les routes (blueprints) de l'application,
facilitant la structure modulaire de l'API. Chaque fonctionnalité (authentification,
blogs, livres, PDF, etc.) est définie dans son propre blueprint pour une meilleure
organisation du code.
"""
from flask import Blueprint
from flask_cors import CORS
from .auth_routes import auth_bp
from .blog_routes import blog_bp
from .book_routes import book_bp
from .pdf_routes import pdf_bp
from .user_routes import user_bp
from .contact_routes import contact_bp
from .question_routes import question_bp
from .system_routes import system_bp

def init_routes(app):
    """
    Initialise tous les blueprints de routes pour l'application Flask.
    
    Args:
        app: L'instance de l'application Flask
    """

    # Enregistrer les blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(blog_bp, url_prefix='/blog')
    app.register_blueprint(book_bp, url_prefix='/books')
    app.register_blueprint(pdf_bp, url_prefix='/pdf')
    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(contact_bp, url_prefix='/contact')
    app.register_blueprint(question_bp, url_prefix='/questions')
    app.register_blueprint(system_bp, url_prefix='/system')