import logging
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

# Initialisation des services
query_service = QueryDataService()

def process_query(app, query, files, new_generate, additional_instructions="", max_page="30", progress_callback=None):
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
        logging.info("=" * 50)

        start_time = time.time()
        device = app['config']['device']
        model = app['model']

        api_key = app['config']['API_KEY']
        model_type_for_response = app['config']['AI_MODEL_TYPE_FOR_REPONSE']
        model_type_for_filter = app['config']['AI_MODEL_TYPE']
        
        send_progress("Clarification de la question")
        finalquery=clarify_question(query,api_key,model_type_for_filter)
        logging.info("Question clarifiée:"+finalquery)
        # Étapes divisées en fonctions
        most_words = extract_keywords(query, send_progress)
        vector_to_compare = vectorize_user_query(query, model, send_progress)

        cached = check_cache(finalquery, most_words, vector_to_compare, query_service, device, new_generate, send_progress)
        if cached:
            return cached

        leaf_matches, tree_matches, file_books = load_and_score_files(app, files, vector_to_compare, most_words, send_progress)

        send_progress("Filtrage initial des résultats...")
        initial_matches = filter_matches_by_score_and_page(leaf_matches, tree_matches, max_page)

        all_matches = llm_filter_matches(initial_matches, query, api_key, model_type_for_filter, send_progress)

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

        batches_to_process = prepare_batches_for_llm(finalquery, all_matches, file_books, send_progress)
        partial_responses = generate_partial_responses(batches_to_process, api_key, model_type_for_response, send_progress)
        final_response = merge_all_responses(app, partial_responses, finalquery, additional_instructions)

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