"""
DTOs pour la gestion des questions et réponses.
"""
from typing import Optional, Dict, Any, List


class QuestionRequestDTO:
    """DTO pour une requête de question."""
    
    def __init__(self, question: str, book_id: str, 
                 context: Optional[str] = None,
                 is_infinite: bool = False,
                 temperature: float = 0.7,
                 model: Optional[str] = None):
        """
        Initialise une requête de question.
        
        Params:
            question: La question posée
            book_id: Identifiant du livre concerné
            context: Contexte supplémentaire pour la question (optionnel)
            is_infinite: Mode infini pour des réponses plus détaillées (optionnel)
            temperature: Température pour le modèle IA (optionnel)
            model: Modèle IA à utiliser (optionnel)
        """
        self.question = question
        self.book_id = book_id
        self.context = context
        self.is_infinite = is_infinite
        self.temperature = temperature
        self.model = model
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QuestionRequestDTO':
        """
        Crée un DTO à partir d'un dictionnaire.
        
        Params:
            data: Dictionnaire contenant les données
            
        Returns:
            Instance du DTO
        """
        return cls(
            question=data.get('question', ''),
            book_id=data.get('bookId', ''),
            context=data.get('context'),
            is_infinite=data.get('isInfinite', False),
            temperature=data.get('temperature', 0.7),
            model=data.get('model')
        )


class DocumentReferenceDTO:
    """DTO pour une référence à un document."""
    
    def __init__(self, page: int, score: float, text: str):
        """
        Initialise une référence à un document.
        
        Params:
            page: Numéro de page
            score: Score de pertinence
            text: Extrait du texte
        """
        self.page = page
        self.score = score
        self.text = text
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentReferenceDTO':
        """
        Crée un DTO à partir d'un dictionnaire.
        
        Params:
            data: Dictionnaire contenant les données
            
        Returns:
            Instance du DTO
        """
        return cls(
            page=data.get('page', 0),
            score=data.get('score', 0.0),
            text=data.get('text', '')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le DTO en dictionnaire.
        
        Returns:
            Dictionnaire représentant le DTO
        """
        return {
            'page': self.page,
            'score': self.score,
            'text': self.text
        }


class AnswerResponseDTO:
    """DTO pour la réponse à une question."""
    
    def __init__(self, answer: str, 
                 references: List[DocumentReferenceDTO],
                 processing_time: float,
                 query_time: float,
                 model_used: str):
        """
        Initialise une réponse à une question.
        
        Params:
            answer: Réponse à la question
            references: Références aux documents utilisés
            processing_time: Temps de traitement total
            query_time: Temps de requête au modèle
            model_used: Modèle utilisé pour la réponse
        """
        self.answer = answer
        self.references = references
        self.processing_time = processing_time
        self.query_time = query_time
        self.model_used = model_used
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le DTO en dictionnaire.
        
        Returns:
            Dictionnaire représentant le DTO
        """
        return {
            'answer': self.answer,
            'references': [ref.to_dict() for ref in self.references],
            'processingTime': self.processing_time,
            'queryTime': self.query_time,
            'modelUsed': self.model_used
        }