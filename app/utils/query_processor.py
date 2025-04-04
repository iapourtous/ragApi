"""
Module de traitement et d'amélioration des requêtes pour l'application RAG API.

Ce module fournit des fonctionnalités pour raffiner, clarifier et décomposer des requêtes
utilisateurs complexes. Il implémente différentes stratégies de traitement comme la
clarification contextuelle, la génération de sous-questions, le traitement parallèle
de sous-requêtes et la fusion intelligente des résultats pour améliorer la qualité
des réponses générées.
"""
# app/utils/query_processor.py

import logging
from app.models.ai_model import AIModel

class QueryProcessor:
    @staticmethod
    def process_subquery(app, subquery, files, new_generate, additional_instructions, max_page, progress_callback):
        """
        Traite une sous-question comme une requête indépendante.
        
        Cette méthode prend une sous-question générée et la traite comme une requête
        à part entière, tout en évitant les problèmes de récursion.
        
        Args:
            app: Configuration de l'application
            subquery: La sous-question à traiter
            files: Liste des fichiers à analyser
            new_generate: Indicateur pour forcer une nouvelle génération
            additional_instructions: Instructions additionnelles pour le LLM
            max_page: Nombre maximal de pages à considérer
            progress_callback: Fonction de rappel pour suivre la progression
            
        Returns:
            str: Réponse générée pour la sous-question
        """
        try:
            # Import local pour éviter l'importation circulaire
            from app.pdf_aiProcessing import process_query
            
            # Créer une copie modifiée des paramètres pour éviter la récursion
            modified_app = dict(app)
            
            result = process_query(
                app=modified_app,
                query=subquery,
                files=files,
                new_generate=new_generate,
                additional_instructions=additional_instructions,
                max_page=max_page,
                progress_callback=lambda msg: progress_callback(f"Sous-question: {msg}"),
                mode_infinity=False,  # Éviter la récursion
                add_section=False     # Ne pas ajouter de sections supplémentaires
            )
            return result.get('LLMresponse', '')
        except Exception as e:
            logging.error(f"Erreur lors du traitement de la sous-question: {e}")
            return f"Erreur lors du traitement de la sous-question: {str(e)}"

    @staticmethod
    def clarify_question_infinity(query, file_books, api_key, model_type):
        """
        Clarifie la question en tenant compte du contexte des livres disponibles.
        
        Cette méthode reformule et précise la question de l'utilisateur en fonction
        du contenu des livres disponibles pour améliorer la pertinence des résultats.
        
        Args:
            query: La question originale
            file_books: Liste de dictionnaires contenant les informations sur les livres disponibles
            api_key: Clé API pour le modèle LLM
            model_type: Type de modèle LLM à utiliser
            
        Returns:
            str: Question clarifiée et reformulée
        """
        books_context = "\n\n".join([
            f"Livre: {book['filename']}\nDescription: {book['description']}"
            for book in file_books if book.get('description')
        ])
        
        prompt = f"""En tant qu'expert en analyse documentaire, reformulez et précisez la question suivante 
    en tenant compte du contenu spécifique des livres disponibles.

    QUESTION INITIALE :
    {query}

    CONTENU DISPONIBLE DANS LES LIVRES :
    {books_context}

    INSTRUCTIONS :
    - Reformulez la question pour qu'elle soit plus précise et adaptée aux sources disponibles
    - Gardez l'intention originale de la question
    - Ajoutez des précisions pertinentes basées sur le contenu des livres
    - Assurez-vous que la question reste claire et concise

    QUESTION REFORMULÉE :"""

        try:
            clarified = AIModel.generate_response(model_type, api_key, prompt)
            logging.info(f"Question clarifiée avec contexte: {clarified}")
            return clarified.strip()
        except Exception as e:
            logging.error(f"Erreur lors de la clarification contextuelle: {e}")
            return query

    @staticmethod
    def generate_subquestions(query, file_books, api_key, model_type):
        """
        Décompose une question complexe en sous-questions plus spécifiques.
        
        Cette méthode analyse la complexité de la question et, si nécessaire,
        la décompose en plusieurs sous-questions pour un traitement plus précis.
        
        Args:
            query: La question à décomposer
            file_books: Liste de dictionnaires contenant les informations sur les livres disponibles
            api_key: Clé API pour le modèle LLM
            model_type: Type de modèle LLM à utiliser
            
        Returns:
            list: Liste des sous-questions ou None si la décomposition n'est pas nécessaire
        """
        books_context = "\n\n".join([
            f"Livre: {book['filename']}\nDescription: {book['description']}"
            for book in file_books if book.get('description')
        ])
        
        prompt = f"""En tant qu'expert en analyse de questions complexes, évaluez si la question suivante 
    nécessite d'être décomposée en sous-questions plus spécifiques, en tenant compte des sources disponibles.

    QUESTION PRINCIPALE :
    {query}

    SOURCES DISPONIBLES :
    {books_context}

    INSTRUCTIONS :
    1. Analysez si la question nécessite une décomposition
    2. Si oui, créez 2 à 5 sous-questions pertinentes
    3. Si non, répondez "DECOMPOSITION NON NECESSAIRE"

    FORMAT DE RÉPONSE :
    - Si décomposition nécessaire : liste numérotée des sous-questions
    - Si non nécessaire : "DECOMPOSITION NON NECESSAIRE"

    ANALYSE ET SOUS-QUESTIONS :"""

        try:
            response = AIModel.generate_response(model_type, api_key, prompt)
            
            if "DECOMPOSITION NON NECESSAIRE" in response.upper():
                return None
                
            subquestions = []
            for line in response.split('\n'):
                if line.strip() and any(c.isdigit() for c in line):
                    question = line.split('.', 1)[-1].strip()
                    if question:
                        subquestions.append(question)
                        
            return subquestions if subquestions else None
            
        except Exception as e:
            logging.error(f"Erreur lors de la génération des sous-questions: {e}")
            return None

    @staticmethod
    def improve_with_subanswers(final_response, sub_responses, api_key, model_type):
        """
        Améliore la réponse finale en intégrant les réponses aux sous-questions.
        
        Cette méthode analyse les réponses obtenues pour chaque sous-question
        et les intègre intelligemment à la réponse principale pour former
        une réponse complète et cohérente.
        
        Args:
            final_response: Réponse principale générée
            sub_responses: Réponses à toutes les sous-questions
            api_key: Clé API pour le modèle LLM
            model_type: Type de modèle LLM à utiliser
            
        Returns:
            str: Réponse améliorée et enrichie
        """
        
        prompt = f"""En tant qu'expert en synthèse documentaire, ton rôle est d'identifier UNIQUEMENT les informations complémentaires des sous-réponses qui peuvent enrichir la réponse principale.

IMPORTANT: Ne répète PAS la réponse principale. Retourne UNIQUEMENT les nouvelles informations à ajouter.

RÉPONSE PRINCIPALE :
{final_response}

RÉPONSES AUX SOUS-QUESTIONS :
{sub_responses}

INSTRUCTIONS :
1. Analyse les sous-réponses pour identifier les informations qui ne sont PAS déjà dans la réponse principale
2. Retourne UNIQUEMENT ces nouvelles informations de manière concise et structurée
3. Si une information est déjà présente dans la réponse principale, ne la mentionne pas
4. Utilise le format Markdown pour la structure

NOUVELLES INFORMATIONS À AJOUTER (uniquement le complément) :"""

        try:
            improved_response = AIModel.generate_response(model_type, api_key, prompt)
            return improved_response
        except Exception as e:
            logging.error(f"Erreur lors de l'amélioration de la réponse: {e}")
            return final_response