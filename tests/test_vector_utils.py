import unittest
import torch
import numpy as np
from app.utils.vector_utils import (
    calculate_similarity,
    deserialize_tensor,
    serialize_tensor,
    get_top_scores,
    vectorize_text,
)
from app.utils.cache_utils import vector_cache

# Création d'une classe mock pour le modèle d'encodage
class MockModel:
    def encode(self, text, convert_to_tensor=True, normalize_embeddings=True):
        # Simuler l'encodage en générant un vecteur basé sur la longueur du texte
        # C'est seulement pour les tests, ne fera pas d'inférence réelle
        vec_length = 384  # Dimension typique pour les modèles sentence-transformers
        # Utiliser la longueur du texte comme seed pour reproducibilité
        seed = sum(ord(c) for c in text)
        np.random.seed(seed)
        # Générer un vecteur aléatoire mais déterministe
        embedding = np.random.randn(vec_length).astype(np.float32)
        # Normalisation optionnelle
        if normalize_embeddings:
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
        # Conversion en tensor si demandé
        if convert_to_tensor:
            return torch.tensor(embedding)
        return embedding
    
    # Simuler un tokenizer pour split_text_into_chunks
    def __init__(self):
        self.tokenizer = self
    
    def tokenize(self, text):
        # Simuler la tokenisation en comptant les mots
        return text.split()

class TestVectorUtils(unittest.TestCase):
    def setUp(self):
        self.device = "cpu"
        # Créer quelques données de test
        self.test_vector = torch.tensor([1.0, 2.0, 3.0])
        self.test_data = [
            {
                "vector_data": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
                "file": "test1.txt",
                "pageBegin": 1,
                "pageEnd": 2,
                "resume": "Test résumé 1",
                "text": "Test texte 1",
                "pageNumber": 1
            },
            {
                "vector_data": [[7.0, 8.0, 9.0]],
                "file": "test2.txt",
                "pageBegin": 3,
                "pageEnd": 4,
                "resume": "Test résumé 2",
                "text": "Test texte 2",
                "pageNumber": 2
            }
        ]

    def test_serialize_deserialize_tensor(self):
        """Test la sérialisation et désérialisation d'un tenseur"""
        original_tensor = torch.tensor([1.0, 2.0, 3.0])
        serialized = serialize_tensor(original_tensor)
        deserialized = deserialize_tensor(serialized, self.device)
        
        self.assertTrue(torch.equal(original_tensor, deserialized))
        self.assertIsInstance(serialized, list)
        self.assertEqual(len(serialized), 3)

    def test_calculate_similarity(self):
        """Test le calcul de similarité entre vecteurs"""
        vector_to_compare = torch.tensor([1.0, 2.0, 3.0])
        scores = calculate_similarity(self.test_data, vector_to_compare, self.device)
        
        self.assertEqual(len(scores), len(self.test_data))
        for score in scores:
            self.assertIn("score", score)
            self.assertIn("file", score)
            self.assertIn("pageBegin", score)
            self.assertIn("pageEnd", score)
            self.assertIn("summary", score)
            self.assertIn("text", score)
            self.assertIn("pageNumber", score)
            self.assertIsInstance(score["score"], float)
            self.assertTrue(0 <= score["score"] <= 1)

    def test_get_top_scores(self):
        """Test la récupération des meilleurs scores"""
        test_scores = [
            {"score": 0.9, "text": "test1"},
            {"score": 0.8, "text": "test2"},
            {"score": 0.7, "text": "test3"},
            {"score": 0.6, "text": "test4"},
            {"score": 0.5, "text": "test5"}
        ]
        
        # Test avec n=3 et threshold=0.6
        top_scores = get_top_scores(test_scores, n=3, threshold=0.6)
        self.assertEqual(len(top_scores), 3)
        self.assertEqual(top_scores[0]["score"], 0.9)
        self.assertEqual(top_scores[-1]["score"], 0.7)
        
        # Test avec threshold élevé
        high_threshold_scores = get_top_scores(test_scores, n=3, threshold=0.85)
        self.assertEqual(len(high_threshold_scores), 1)
        
        # Test avec n plus grand que le nombre de scores disponibles
        all_scores = get_top_scores(test_scores, n=10, threshold=0.0)
        self.assertEqual(len(all_scores), 5)

    def test_vectorization_cache(self):
        """Test le cache de vectorisation"""
        # Création d'un modèle mock
        model = MockModel()
        
        # Nettoyer le cache pour éviter les interférences
        vector_cache.lru_cache.clear()
        
        # Premier appel, devrait créer un vecteur
        test_text = "This is a test for vectorization."
        embedding1 = vectorize_text(test_text, model, prefix="query: ", use_cache=True, chunk_content=False)
        
        # Vérifier que l'embedding a été calculé
        # Si chunk_content=False, on doit obtenir un tenseur
        # Si chunk_content=True, on obtient une liste de tenseurs
        if isinstance(embedding1, list):
            self.assertTrue(len(embedding1) > 0)
            self.assertIsInstance(embedding1[0], torch.Tensor)
        else:
            self.assertIsInstance(embedding1, torch.Tensor)
        
        # Vérifier les statistiques du cache (1 miss, 0 hit)
        stats = vector_cache.get_stats()
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hits"], 0)
        
        # Deuxième appel, devrait utiliser le cache
        embedding2 = vectorize_text(test_text, model, prefix="query: ", use_cache=True, chunk_content=False)
        
        # Vérifier que l'embedding est identique
        if isinstance(embedding1, list):
            self.assertEqual(len(embedding1), len(embedding2))
            for e1, e2 in zip(embedding1, embedding2):
                self.assertTrue(torch.all(torch.eq(e1, e2)))
        else:
            self.assertTrue(torch.all(torch.eq(embedding1, embedding2)))
        
        # Vérifier les statistiques du cache (1 miss, 1 hit)
        stats = vector_cache.get_stats()
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hits"], 1)
        
        # Test avec un texte différent
        new_text = "This is another test."
        embedding3 = vectorize_text(new_text, model, prefix="query: ", use_cache=True, chunk_content=False)
        
        # Vérifier que l'embedding est différent du premier
        if isinstance(embedding1, list) and isinstance(embedding3, list):
            if len(embedding1) == len(embedding3):
                # Vérifier qu'au moins un tenseur est différent
                any_different = False
                for e1, e3 in zip(embedding1, embedding3):
                    if not torch.all(torch.eq(e1, e3)):
                        any_different = True
                        break
                self.assertTrue(any_different)
            else:
                # Différentes longueurs = différents embeddings
                pass
        elif not isinstance(embedding1, list) and not isinstance(embedding3, list):
            self.assertFalse(torch.all(torch.eq(embedding1, embedding3)))
        else:
            # Un est liste, l'autre pas = différents types d'embeddings
            pass
        
        # Vérifier les statistiques du cache (2 misses, 1 hit)
        stats = vector_cache.get_stats()
        self.assertEqual(stats["misses"], 2)
        self.assertEqual(stats["hits"], 1)
        
        # Test avec désactivation du cache
        # Ce devrait être un nouveau calcul malgré la présence en cache
        embedding4 = vectorize_text(test_text, model, prefix="query: ", use_cache=False, chunk_content=False)
        
        # Vérifier les statistiques du cache (inchangées, car cache non utilisé)
        stats = vector_cache.get_stats()
        self.assertEqual(stats["misses"], 2)
        self.assertEqual(stats["hits"], 1)

if __name__ == '__main__':
    unittest.main()
