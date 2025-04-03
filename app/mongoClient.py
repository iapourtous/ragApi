"""
Interface client pour MongoDB utilisée par l'application RAG API.

Ce module fournit une classe Client qui encapsule la connexion à MongoDB
et simplifie l'accès aux collections. Il s'agit d'une abstraction légère 
au-dessus de pymongo.MongoClient pour faciliter la gestion des connexions 
dans l'application.
"""
from pymongo import MongoClient

class Client:
    def __init__(self, db_name, uri="mongodb://localhost:27017/"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        print(f"Connected to MongoDB database: {db_name}")
    
    def get_collection(self, collection_name):
        return self.db[collection_name]
    