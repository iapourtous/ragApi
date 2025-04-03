"""
Module de routes pour la génération de questions basées sur le contenu des livres.

Ce module expose des endpoints API permettant de générer automatiquement
des questions pertinentes à partir du contenu extrait de livres spécifiques,
en utilisant des modèles de langage.

Routes:
    /generate-questions: Génère des questions sur un sujet spécifique
        en se basant sur le contenu extrait d'un livre.
"""

import logging
import random
import time
from flask import Blueprint, request, jsonify, current_app
from app.services.book_service import BookService
from app.utils.file_utils import load_processed_data
from app.utils.ai_utils import estimate_tokens
from app.models.ai_model import AIModel
from app.utils.auth_utils import token_required
from app.dto.question_dto import QuestionRequestDTO, AnswerResponseDTO, DocumentReferenceDTO

# Création du Blueprint pour la génération de questions
question_bp = Blueprint('question', __name__)
book_service = BookService()
ai_model = AIModel()

# Seuil maximal de tokens pour le contexte (vous pouvez ajuster cette valeur)
MAX_CONTEXT_TOKENS = 3000

def retrieve_relevant_passages(files_book, question, top_k=5):
    """
    Récupère les passages les plus pertinents pour une question donnée.
    
    Cette fonction est un exemple simplifié du processus de récupération
    dans un système RAG. Dans une implémentation réelle, elle utiliserait
    la recherche vectorielle pour trouver les passages les plus pertinents.
    
    Args:
        files_book: L'objet FilesBook contenant les données du livre
        question: La question posée par l'utilisateur
        top_k: Nombre de passages à récupérer
        
    Returns:
        Liste des passages pertinents avec leur score et texte
    """
    # Exemple simpliste - dans un système réel, vous utiliseriez
    # la recherche vectorielle pour trouver les passages pertinents
    # basés sur la similarité avec la question
    
    relevant_passages = []
    
    # Parcourir les différents niveaux de descriptions
    for level, descriptions in enumerate(files_book.descriptions):
        for index, desc in enumerate(descriptions):
            # Simuler un score de pertinence (aléatoire pour cet exemple)
            score = random.uniform(0.5, 0.95)
            
            if len(relevant_passages) < top_k or score > min([p['score'] for p in relevant_passages], default=0):
                passage = {
                    'level': level,
                    'index': index,
                    'page': desc.get('page', 0),
                    'text': desc.get('text', ''),
                    'score': score
                }
                
                relevant_passages.append(passage)
                
                # Garder uniquement les top_k meilleurs passages
                if len(relevant_passages) > top_k:
                    relevant_passages.sort(key=lambda x: x['score'], reverse=True)
                    relevant_passages = relevant_passages[:top_k]
    
    return relevant_passages

@question_bp.route('/ask', methods=['POST'])
@token_required
def ask_question(current_user):
    """
    Route pour poser une question sur le contenu d'un livre.
    
    Reçoit une question et l'ID d'un livre, et utilise le système RAG pour
    trouver les passages pertinents et générer une réponse.
    
    Returns:
        JSON: La réponse générée et les références aux passages utilisés
    """
    start_time = time.time()
    
    # Conversion de la requête JSON en DTO
    question_request = QuestionRequestDTO.from_dict(request.json)
    
    # Validation des données
    if not question_request.question or not question_request.book_id:
        return jsonify({'message': 'Question and book ID are required'}), 400
    
    # Récupération du livre
    book = book_service.get_book_by_id(question_request.book_id)
    if not book:
        return jsonify({'message': 'Book not found'}), 404
    
    # Vérification des droits d'accès
    if not book.get('public') and book.get('owner_id') != current_user.get('id'):
        return jsonify({'message': 'You do not have access to this book'}), 403
    
    # Chargement des données vectorisées du livre
    files_book = load_processed_data(current_app, book.get('pdf_path'))
    if not files_book:
        return jsonify({'message': 'Unable to load processed book data'}), 500
    
    # Récupération des passages pertinents (cette partie serait remplacée par votre logique RAG)
    # Supposons que nous avons une fonction retrieve_relevant_passages dans votre système
    relevant_passages = retrieve_relevant_passages(files_book, question_request.question)
    
    if not relevant_passages:
        return jsonify({'message': 'No relevant passages found'}), 404
    
    # Construction du contexte pour la génération de réponse
    context = "\n\n".join([passage['text'] for passage in relevant_passages])
    
    # Configuration du modèle à utiliser
    model_type = question_request.model or current_app.config['AI_MODEL_TYPE_FOR_RESPONSE']
    
    # Appel à l'IA pour générer la réponse
    query_start_time = time.time()
    try:
        answer = ai_model.generate_response(
            model_type,
            current_app.config['API_KEY'],
            f"""
Vous êtes un système d'aide aux questions basé sur les documents. Répondez à la question en vous 
basant uniquement sur les extraits fournis. Si vous ne trouvez pas la réponse dans les extraits, 
indiquez-le honnêtement au lieu d'inventer une réponse.

QUESTION: {question_request.question}

CONTEXTE SUPPLÉMENTAIRE (facultatif): {question_request.context or ""}

EXTRAITS:
{context}

MODE: {"Détaillé" if question_request.is_infinite else "Concis"}

RÉPONSE EN FRANÇAIS:
""",
            temperature=question_request.temperature
        )
    except Exception as e:
        logging.error(f"Error generating answer: {e}")
        return jsonify({'message': 'Error generating answer'}), 500
    
    query_time = time.time() - query_start_time
    processing_time = time.time() - start_time
    
    # Création des références aux documents
    references = []
    for passage in relevant_passages:
        reference = DocumentReferenceDTO(
            page=passage.get('page', 0),
            score=passage.get('score', 0.0),
            text=passage.get('text', '')[:300]  # Tronquer le texte pour la réponse
        )
        references.append(reference)
    
    # Création du DTO de réponse
    answer_response = AnswerResponseDTO(
        answer=answer,
        references=references,
        processing_time=processing_time,
        query_time=query_time,
        model_used=model_type
    )
    
    return jsonify(answer_response.to_dict()), 200

@question_bp.route('/generate-questions', methods=['POST'])
@token_required
def generate_questions(current_user):
    """
    Route qui reçoit en entrée le titre d'un livre, une liste de pages (chaque élément doit contenir
    "level" et "index" correspondant à FilesBook.descriptions) et un sujet.
    
    Elle génère en sortie une liste de questions sur le sujet, basées sur le contenu extrait des pages lues.
    Pour ne pas dépasser la limite de tokens du contexte, les pages sont ajoutées de manière aléatoire
    jusqu'à atteindre un seuil fixé.
    """
    data = request.get_json()
    title = data.get("title")
    pages = data.get("pages")  # liste de dictionnaires : [{'level': <int>, 'index': <int>}, ...]
    subject = data.get("subject")
    
    if not title or not pages or not subject:
        return jsonify({"error": "Le titre, les pages et le sujet sont requis."}), 400
    
    # Récupération du livre à partir du titre
    book_data = book_service.get_book_by_title(title)
    if not book_data:
        return jsonify({"error": "Livre non trouvé."}), 404
    
    # Chargement des données traitées (FilesBook) pour le livre
    files_book = load_processed_data(current_app, book_data.get("pdf_path"))
    if not files_book:
        return jsonify({"error": "Impossible de charger les données traitées du livre."}), 500
    
    # Récupération des textes des pages indiquées
    context_texts = []
    for page_info in pages:
        level = page_info.get("level")
        index = page_info.get("index")
        try:
            # Vérifier que le niveau existe et que l'index est valide
            if level is None or index is None:
                continue
            if level < 0 or level >= len(files_book.descriptions):
                continue
            level_descriptions = files_book.descriptions[level]
            if index < 0 or index >= len(level_descriptions):
                continue
            # Extraction du texte de la page (en supposant que le dictionnaire possède la clé "text")
            page_text = level_descriptions[index].get("text", "")
            if page_text:
                context_texts.append(page_text)
        except Exception as e:
            logging.error(f"Erreur lors de la récupération de la page (level={level}, index={index}) : {e}")
    
    if not context_texts:
        return jsonify({"error": "Aucun texte valide trouvé dans les pages spécifiées."}), 400
    
    # Mélanger aléatoirement les pages pour éviter un ordre biaisé et accumuler jusqu'à la limite de tokens
    random.shuffle(context_texts)
    context_combined = ""
    for text in context_texts:
        # On ajoute un séparateur pour distinguer les pages (par exemple, deux sauts de ligne)
        new_context = context_combined + "\n\n" + text if context_combined else text
        if estimate_tokens(new_context) <= MAX_CONTEXT_TOKENS:
            context_combined = new_context
        else:
            # Si l'ajout de ce texte dépasse la limite, on passe au suivant
            continue
    
    if not context_combined:
        return jsonify({"error": "Le contexte est vide après application de la limite de tokens."}), 400
    
    # Construction du prompt pour l'IA
    prompt = f"""
Vous êtes un expert en pédagogie et en génération de questions.
Sur la base du contenu ci-dessous et en vous concentrant sur le sujet "{subject}", 
générez une liste de questions pertinentes. Les questions doivent être concises, formulées en français 
et adaptées aux informations présentes dans le contexte.

CONTEXTE :
{context_combined}

SUJET : {subject}

Veuillez lister uniquement les questions, chacune sur une nouvelle ligne, sans explications supplémentaires.
"""
    try:
        questions_response = ai_model.generate_response(
            current_app.config['AI_MODEL_TYPE_FOR_REPONSE'],
            current_app.config['API_KEY'],
            prompt
        )
    except Exception as e:
        logging.error(f"Erreur lors de la génération des questions : {e}")
        return jsonify({"error": "Erreur lors de la génération des questions par l'IA."}), 500
    
    return jsonify({"questions": questions_response}), 200