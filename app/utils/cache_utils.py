"""
Utilitaires de mise en cache pour l'application RAG API.

Ce module fournit des implémentations de cache utilisées pour optimiser les performances
de l'application, notamment un cache LRU (Least Recently Used) thread-safe pour stocker
temporairement des données fréquemment accédées, ainsi qu'un cache spécialisé pour
les vecteurs d'embeddings.
"""
import logging
import hashlib
import pickle
from threading import Lock
from collections import OrderedDict
import torch

class LRUCache:
    """
    Implémentation d'un cache de type LRU (Least Recently Used).
    Utilise un OrderedDict pour maintenir l'ordre des éléments en fonction de leur utilisation.
    Un verrou (Lock) est utilisé pour assurer la sécurité des threads lors des opérations concurrentes.
    """

    def __init__(self, capacity):
        """
        Initialise le cache avec une capacité maximale.

        :param capacity: Nombre maximal d'éléments que le cach8e peut contenir.
        """
        self.cache = OrderedDict()
        self.capacity = capacity
        self.lock = Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key):
        """
        Récupère la valeur associée à la clé donnée si elle existe dans le cache.
        Met à jour l'ordre des éléments pour refléter l'accès récent.

        :param key: Clé de l'élément à récupérer.
        :return: Valeur associée à la clé si elle existe, sinon None.
        """
        with self.lock:
            if key not in self.cache:
                # La clé n'existe pas dans le cache
                self.misses += 1
                return None
            # Déplacer l'élément en fin de l'OrderedDict pour indiquer un accès récent
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]

    def put(self, key, value):
        """
        Ajoute un élément au cache ou met à jour la valeur si la clé existe déjà.
        Si le cache dépasse sa capacité, l'élément le moins récemment utilisé est supprimé.

        :param key: Clé de l'élément à ajouter ou mettre à jour.
        :param value: Valeur de l'élément à ajouter ou mettre à jour.
        """
        with self.lock:
            if key in self.cache:
                # Si la clé existe déjà, déplacer l'élément en fin pour indiquer un accès récent
                self.cache.move_to_end(key)
            # Ajouter ou mettre à jour l'élément dans le cache
            self.cache[key] = value
            if len(self.cache) > self.capacity:
                # Si le cache dépasse la capacité, supprimer l'élément le moins récemment utilisé (premier élément)
                removed_key, removed_value = self.cache.popitem(last=False)
                logging.debug(f"Élément supprimé du cache LRU: {removed_key} -> {removed_value}")
    
    def clear(self):
        """
        Vide complètement le cache.
        """
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self):
        """
        Renvoie les statistiques d'utilisation du cache.
        
        :return: Dictionnaire contenant le nombre d'accès réussis (hits), d'échecs (misses),
                 le taux de succès (hit_rate) et la taille actuelle du cache.
        """
        with self.lock:
            total_queries = self.hits + self.misses
            hit_rate = self.hits / total_queries if total_queries > 0 else 0
            return {
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "size": len(self.cache),
                "capacity": self.capacity
            }

class VectorizationCache:
    """
    Cache spécialisé pour stocker les vecteurs d'embeddings.
    Utilise un hachage des textes pour les clés et permet la mise en cache 
    de tenseurs PyTorch et d'autres objets sérialisables.
    """
    
    def __init__(self, capacity=1000):
        """
        Initialise le cache de vectorisation.
        
        :param capacity: Nombre maximal d'entrées dans le cache.
        """
        self.lru_cache = LRUCache(capacity)
        self.device_map = {}  # Map pour suivre sur quel device chaque tenseur a été mis
    
    def _hash_text(self, text, prefix="", chunk_content=True):
        """
        Génère un hash unique pour un texte avec ses paramètres de vectorisation.
        
        :param text: Texte à hacher
        :param prefix: Préfixe ajouté au texte avant vectorisation
        :param chunk_content: Indicateur si le texte sera découpé en chunks
        :return: Chaîne de hachage
        """
        # Créer une clé unique basée sur tous les paramètres
        key_parts = [text, prefix, str(chunk_content)]
        combined = "|".join(key_parts)
        
        # Hacher la clé pour éviter les longues chaînes comme clés de cache
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def get(self, text, prefix="", chunk_content=True, device=None):
        """
        Récupère un vecteur d'embedding préalablement mis en cache.
        
        :param text: Texte dont on veut l'embedding
        :param prefix: Préfixe ajouté au texte lors de la vectorisation
        :param chunk_content: Indicateur si le texte est découpé en chunks
        :param device: Device sur lequel placer le tenseur (None = laisser sur le device d'origine)
        :return: Embedding vectorisé ou None si pas dans le cache
        """
        key = self._hash_text(text, prefix, chunk_content)
        cached_data = self.lru_cache.get(key)
        
        if cached_data is None:
            return None
        
        # Désérialiser l'embedding
        embedding = pickle.loads(cached_data)
        
        # Si c'est un tenseur PyTorch et qu'un device est spécifié, le déplacer
        if isinstance(embedding, torch.Tensor) and device is not None:
            embedding = embedding.to(device)
            # Mettre à jour la map de device
            self.device_map[key] = device
            
        return embedding
    
    def put(self, text, embedding, prefix="", chunk_content=True):
        """
        Met en cache un vecteur d'embedding.
        
        :param text: Texte source de l'embedding
        :param embedding: Vecteur d'embedding à mettre en cache
        :param prefix: Préfixe ajouté au texte lors de la vectorisation
        :param chunk_content: Indicateur si le texte a été découpé en chunks
        """
        key = self._hash_text(text, prefix, chunk_content)
        
        # Si c'est un tenseur PyTorch, noter son device actuel
        if isinstance(embedding, torch.Tensor):
            self.device_map[key] = embedding.device
            
        # Sérialiser l'embedding pour le stockage
        serialized = pickle.dumps(embedding)
        self.lru_cache.put(key, serialized)
    
    def get_stats(self):
        """
        Renvoie les statistiques du cache de vectorisation.
        
        :return: Statistiques du cache LRU sous-jacent
        """
        return self.lru_cache.get_stats()

# Instances globales de cache
memory_cache = LRUCache(capacity=30)
vector_cache = VectorizationCache(capacity=2000)  # Cache dédié pour les vecteurs d'embedding