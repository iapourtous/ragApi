from ..mongoClient import Client
from bson import ObjectId
import logging
import torch
from sentence_transformers import util
from ..utils.text_utils import contain_key

class QueryDataService:
    """
    Service gérant les opérations liées aux requêtes et leurs données associées dans la base de données.
    Permet la recherche, la sauvegarde et le traitement des votes sur les requêtes.
    """

    def __init__(self):
        """
        Initialise le service avec une connexion à la base de données MongoDB.
        Configure la collection pour les données de requêtes.
        """
        self.client = Client("rag")
        self.collection = self.client.get_collection("queryDatas")

    def search_similar_query(self, query, most_words, vector_to_compare, device):
        """
        Recherche une requête similaire dans la base de données en utilisant une comparaison vectorielle
        et une correspondance de mots-clés.

        Args:
            query (str): La requête à rechercher
            most_words (list): Liste des mots-clés importants à rechercher
            vector_to_compare (tensor): Vecteur de la requête à comparer
            device (str): Dispositif de calcul ('cpu' ou 'cuda')

        Returns:
            dict: La requête la plus similaire trouvée si le score dépasse 0.98, None sinon
        """
        logging.info(f"Recherche de requêtes similaires sur {device}")
        query_datas = self.collection.find()
        best_score = 0
        best_response = None

        for mquery in query_datas:
            if contain_key(mquery["query"], most_words):
                f_tensor = torch.tensor(mquery["vector_data"]).to(device)
                f_tensor_to_compare = torch.tensor(vector_to_compare).to(device)
                score = util.cos_sim(f_tensor, f_tensor_to_compare).item()

                if score > best_score:
                    best_score = score
                    best_response = mquery

        if best_score > 0.98:
            best_response["_id"] = str(best_response["_id"])
            return best_response
        return None

    def save_query(self, query, vector_to_compare, response_data):
        """
        Sauvegarde une nouvelle requête et sa réponse dans la base de données.

        Args:
            query (str): La requête à sauvegarder
            vector_to_compare (tensor): Le vecteur représentant la requête
            response_data (dict): Les données de réponse associées à la requête

        Returns:
            str: L'ID de la requête sauvegardée, None en cas d'erreur
        """
        try:
            query_data = {
                "response": response_data,
                "query": query,
                "vector_data": [tensor.tolist() for tensor in vector_to_compare],
                "upvotes": 0,
                "downvotes": 0
            }
            result = self.collection.insert_one(query_data)
            return str(result.inserted_id)
        except Exception as e:
            logging.error(f"Erreur lors de la sauvegarde de la requête : {e}")
            return None

    def process_vote(self, query_id, vote_type):
        """
        Traite les votes (positifs ou négatifs) pour une requête donnée.

        Args:
            query_id (str): L'ID de la requête à voter
            vote_type (str): Le type de vote ('upvote' ou 'downvote')

        Returns:
            bool: True si le vote a été traité avec succès, False sinon
        """
        try:
            query_data = self.collection.find_one({"_id": ObjectId(query_id)})
            if not query_data:
                return False

            if vote_type not in ['upvote', 'downvote']:
                return False

            update_field = "upvotes" if vote_type == 'upvote' else "downvotes"
            self.collection.update_one(
                {"_id": ObjectId(query_id)},
                {"$inc": {update_field: 1}}
            )
            return True
        except Exception as e:
            logging.error(f"Erreur lors du traitement du vote : {e}")
            return False