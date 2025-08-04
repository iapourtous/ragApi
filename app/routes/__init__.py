"""
Module d'initialisation des routes pour l'application RAG API.

Ce module centralise l'enregistrement de toutes les routes (blueprints) de l'application,
facilitant la structure modulaire de l'API. L'API se concentre sur les fonctionnalités
essentielles : gestion des livres, traitement PDF, questions RAG et système.
"""
from flask import Blueprint
from flask_cors import CORS
from .book_routes import book_bp
from .pdf_routes import pdf_bp
from .question_routes import question_bp
from .system_routes import system_bp

def init_routes(app):
    """
    Initialise tous les blueprints de routes pour l'application Flask.
    
    Args:
        app: L'instance de l'application Flask
    """

    # Enregistrer les blueprints essentiels
    app.register_blueprint(book_bp, url_prefix='/book')
    app.register_blueprint(pdf_bp, url_prefix='/pdf')
    app.register_blueprint(question_bp, url_prefix='/question')
    app.register_blueprint(system_bp, url_prefix='/system')