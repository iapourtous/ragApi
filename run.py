"""
Point d'entrée principal de l'application RAG API.

Ce script importe la fonction create_app du package app, crée une instance
de l'application Flask et la démarre avec les paramètres spécifiés lorsqu'il
est exécuté directement.
"""
from app import create_app
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081, debug=True)
    