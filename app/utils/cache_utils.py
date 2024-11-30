import logging
from threading import Lock
from collections import OrderedDict

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
                return None
            # Déplacer l'élément en fin de l'OrderedDict pour indiquer un accès récent
            self.cache.move_to_end(key)
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