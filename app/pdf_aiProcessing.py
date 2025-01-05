from itertools import accumulate
import logging
from os import access
from re import sub
import time

from .utils.ai_utils import clarify_question

from .utils.pdfQuery_utils import (
    extract_keywords,
    vectorize_user_query,
    check_cache,
    load_and_score_files,
    filter_matches_by_score_and_page,
    llm_filter_matches,
    prepare_batches_for_llm,
    generate_partial_responses,
    merge_all_responses,
    save_response_to_db
)
from .services.queryData_service import QueryDataService
from .services.book_service import BookService
from .utils.query_processor import QueryProcessor
from app.services import book_service

# Initialisation des services
query_service = QueryDataService()
book_service=BookService()

def process_query(app, query, files, new_generate, additional_instructions="", max_page="30", progress_callback=None, mode_infinity=False, add_section=True):
    def send_progress(message):
        if progress_callback:
            progress_callback(message)

    try:
        partial_responses = []
        batches_to_process = []

        send_progress("Démarrage du traitement...")
        logging.info("=" * 50)
        logging.info("STARTING QUERY PROCESSING")
        logging.info(f"Query: {query}")
        logging.info(f"Files to analyze: {files}")
        logging.info(f"Force new generation: {new_generate}")
        logging.info(f"Additional instructions: {additional_instructions}")
        logging.info(f"Mode Infinity: {mode_infinity}")
        logging.info("=" * 50)

        start_time = time.time()
        device = app['config']['device']
        model = app['model']

        api_key = app['config']['API_KEY']
        model_type_for_response = app['config']['AI_MODEL_TYPE_FOR_REPONSE']
        model_type_for_filter = app['config']['AI_MODEL_TYPE']
        
        send_progress("Clarification de la question")
        file_books = []
        for f in files:
            # Récupère le livre par son nom de fichier PDF
            book_data = book_service.get_book_by_filename(f)
            if book_data and 'description' in book_data and book_data['description']:
                file_books.append({
                    "filename": f,
                    "description": book_data['description']
                })
            else:
                # Si aucune description n'est trouvée dans la DB, vous pouvez 
                # soit ignorer ce livre, soit gérer le cas différemment
                logging.warning(f"Aucune description trouvée pour le livre associé au fichier {f}")
        # Clarifier la question
        finalquery = QueryProcessor.clarify_question_infinity(query, file_books, api_key, model_type_for_filter)
        logging.info("Question clarifiée:"+finalquery)
        accumulated_subqueries = ""
        if mode_infinity:
            # Trouver des sous-questions
            subqueries = QueryProcessor.generate_subquestions(finalquery, file_books, api_key, model_type_for_filter)
            logging.info("Sous-questions trouvées:"+str(subqueries))
            # Traitement des sous-questions
            # Accumules les sous-reponses dans accumulated_subqueries
            for subquery in subqueries:
                subresponse = QueryProcessor.process_subquery(app, subquery, files, new_generate, additional_instructions, max_page, progress_callback)
                accumulated_subqueries += subresponse
            logging.info("Sous-reponses accumulées:"+accumulated_subqueries)
        # Suite du pipeline standard (mots clés, vectorisation, cache, etc.)
        most_words = extract_keywords(query, send_progress)
        vector_to_compare = vectorize_user_query(finalquery if not mode_infinity else query, model, send_progress)

        cached = check_cache(finalquery, most_words, vector_to_compare, query_service, device, new_generate, send_progress)
        if cached:
            return cached

        leaf_matches, tree_matches, processed_file_books = load_and_score_files(app, files, vector_to_compare, most_words, send_progress)

        send_progress("Filtrage initial des résultats...")
        initial_matches = filter_matches_by_score_and_page(leaf_matches, tree_matches, max_page)

        all_matches = llm_filter_matches(initial_matches, finalquery, api_key, model_type_for_filter, send_progress)

        if not all_matches:
            send_progress("Aucune correspondance pertinente trouvée.")
            return {
                "LLMresponse": "Aucune correspondance pertinente n'a été trouvée dans les documents fournis.",
                "documents": [],
                "matches": {
                    "leaf_matches": [],
                    "tree_matches": []
                }
            }

        batches_to_process = prepare_batches_for_llm(finalquery, all_matches, processed_file_books, send_progress)
        partial_responses = generate_partial_responses(batches_to_process, api_key, model_type_for_response, send_progress=send_progress)
        final_response = merge_all_responses(app, partial_responses, finalquery, additional_instructions, send_progress=send_progress, add_section=add_section)
        if mode_infinity and accumulated_subqueries:
            final_response += "\n"+QueryProcessor.improve_with_subanswers(final_response, accumulated_subqueries, api_key, model_type_for_response)
        response_data = {
            "LLMresponse": final_response,
            "documents": [],
            "matches": {
                "all_matches": all_matches,
            }
        }

        response_data = save_response_to_db(query_service, query, vector_to_compare, response_data, send_progress)

        execution_time = time.time() - start_time
        logging.info("=" * 50)
        logging.info("END OF QUERY PROCESSING")
        logging.info(f"Total execution time: {execution_time:.2f} seconds")
        logging.info(f"Number of batches processed: {len(batches_to_process)}")
        logging.info(f"Number of partial responses: {len(partial_responses)}")
        logging.info("=" * 50)

        send_progress("Traitement terminé.")
        return response_data

    except Exception as e:
        logging.error(f"Error in process_query: {e}")
        logging.exception("Details of the error:")
        if progress_callback:
            progress_callback(f"Erreur : {str(e)}")
        return {
            "LLMresponse": f"An error occurred during query processing: {str(e)}",
            "documents": [],
            "matches": {
                "leaf_matches": [],
                "tree_matches": []
            }
        }