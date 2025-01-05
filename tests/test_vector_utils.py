import unittest
import torch
from app.utils.vector_utils import (
    calculate_similarity,
    deserialize_tensor,
    serialize_tensor,
    get_top_scores,
)

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

if __name__ == '__main__':
    unittest.main()
