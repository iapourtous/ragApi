"""
Interface WSGI pour l'application RAG API.

Ce module crée une instance de l'application Flask qui peut être utilisée par des serveurs
WSGI comme Gunicorn ou uWSGI en production. L'objet 'application' est le point d'entrée
standard pour les serveurs WSGI.
"""
from app import create_app

application = create_app()