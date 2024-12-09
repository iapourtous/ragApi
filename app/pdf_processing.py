import logging
import time
import torch
from sentence_transformers import util
from concurrent.futures import ThreadPoolExecutor, as_completed

from .utils.text_utils import contain_key, search_upper_words, vectorize_query
from .utils.file_utils import load_processed_data
from .utils.ai_utils import (
    estimate_tokens,
    generate_ai_response,
    generate_combined_documentation,
    merge_responses,filter_match_by_llm
)
from .services.queryData_service import QueryDataService

# Initialisation des services
query_service = QueryDataService()
num_workers = 5

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
        model_type_for_filter= app['config']['AI_MODEL_TYPE']

        send_progress("Extraction des mots-clés...")
        most_words = search_upper_words(query)
        logging.info(f"Extracted keywords: {most_words}")

        send_progress("Vectorisation de la requête...")
        vector_to_compare = vectorize_query(query, model)
        logging.info("Query vectorization completed")

        if new_generate != "new":
            send_progress("Vérification du cache...")
            logging.info("Searching in cache...")
            cached_response = query_service.search_similar_query(
                query, 
                most_words, 
                vector_to_compare, 
                device
            )
            if cached_response:
                send_progress("Réponse trouvée dans le cache, envoi de la réponse.")
                logging.info("Response found in cache")
                return cached_response['response']
            logging.info("No cached response found")

        leaf_matches = []
        tree_matches = []
        documents = {}
        file_books = {}

        # Traitement de chaque fichier
        for file in files:
            send_progress(f"Chargement du fichier {file}...")
            logging.info(f"\nProcessing file: {file}")
            loaded_book = load_processed_data(app, file)
            if loaded_book is None:
                logging.warning(f"Unable to load data for: {file}")
                continue

            logging.info(f"Data loaded successfully for: {file}")
            send_progress(f"Analyse des pages du fichier {file}...")

            # Traitement du niveau feuille (pages)
            leaf_level = loaded_book.descriptions[0]
            leaf_vectors = loaded_book.descriptions_vectorized[0]
            logging.info(f"Analyzing {len(leaf_level)} leaf nodes")

            leaf_matches_count = 0
            keywords_matches_count = 0
            for desc, vec in zip(leaf_level, leaf_vectors):
                if most_words and not contain_key(desc['text'], most_words):
                    continue

                keywords_matches_count += 1

                score = float(util.cos_sim(
                    torch.tensor(vec).to(device),
                    vector_to_compare.to(device)
                ))

                leaf_matches.append({
                    'text': desc['text'],
                    'score': score,
                    'page_range': desc['page_range'],
                    'file': file
                })
                leaf_matches_count += 1

            logging.info(f"Passages containing keywords: {keywords_matches_count}")
            logging.info(f"Leaf level matches after scoring: {leaf_matches_count}")

            # Traitement des nœuds de l'arbre
            for level_idx in range(1, len(loaded_book.descriptions)):
                level = loaded_book.descriptions[level_idx]
                vectors = loaded_book.descriptions_vectorized[level_idx]
                logging.info(f"Analyzing level {level_idx} with {len(level)} nodes")

                tree_matches_count = 0
                tree_keywords_matches = 0
                for node, vec in zip(level, vectors):
                    if most_words and not contain_key(node['text'], most_words):
                        continue

                    tree_keywords_matches += 1

                    score = float(util.cos_sim(
                        torch.tensor(vec).to(device),
                        vector_to_compare.to(device)
                    ))

                    tree_matches.append({
                        'text': node['text'],
                        'score': score,
                        'page_range': node['page_range'],
                        'file': file
                    })
                    tree_matches_count += 1

                logging.info(f"Tree nodes containing keywords: {tree_keywords_matches}")
                logging.info(f"Tree level matches after scoring: {tree_matches_count}")

            file_books[file] = loaded_book

        send_progress("Filtrage initial des résultats...")
        # Combinaison et tri des correspondances
        all_matches = []
        for match in leaf_matches + tree_matches:
            try:
                if 'Pages' in match['page_range']:
                    page_num = int(match['page_range'].split(' ')[1])
                else:
                    page_num = int(match['page_range'].split(' ')[1])
            except:
                page_num = 9999

            match['page_num'] = page_num
            all_matches.append(match)

        all_matches.sort(key=lambda x: (-x['score'], x['page_num']))

        MAX_MATCHES = int(max_page)
        initial_matches = all_matches[:MAX_MATCHES]

        send_progress("Filtrage par LLM des passages retenus...")
        filtered_matches = []
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_match = {
                executor.submit(filter_match_by_llm, match, query, api_key, model_type_for_filter): match
                for match in initial_matches
            }
            for future in as_completed(future_to_match):
                match = future_to_match[future]
                try:
                    is_relevant = future.result()
                    if is_relevant:
                        filtered_matches.append(match)
                        logging.info(f"Page {match['page_num']} conservée (score: {match['score']:.3f})")
                    else:
                        logging.info(f"Page {match['page_num']} retirée (score: {match['score']:.3f})")
                except Exception as exc:
                    logging.error(f"An error occurred during LLM filtering of a match: {exc}")

        all_matches = filtered_matches
        all_matches.sort(key=lambda x: x['page_num'])

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

        send_progress("Préparation des lots pour la génération de la réponse...")
        main_stack = all_matches.copy()
        virtual_stack = []

        while main_stack:
            current_match = main_stack.pop(0)
            virtual_stack.append(current_match)

            temp_docs = {}
            for match in virtual_stack:
                file = match['file']
                if file not in temp_docs:
                    temp_docs[file] = {
                        'filename': file,
                        'description': file_books[file].description,
                        'matches': []
                    }
                temp_docs[file]['matches'].append(match)

            documentation = generate_combined_documentation(temp_docs.values())
            estimated_tokens = estimate_tokens(documentation)

            if estimated_tokens > 14000:
                virtual_stack.pop()
                main_stack.insert(0, current_match)

                documentation = generate_combined_documentation([{
                    'filename': doc['filename'],
                    'description': doc['description'],
                    'matches': doc['matches']
                } for doc in temp_docs.values()])

                batch_data = {
                    'query': query,
                    'documentation': documentation,
                    'additional_instructions': additional_instructions
                }
                batches_to_process.append(batch_data)
                virtual_stack = []

        if virtual_stack:
            temp_docs = {}
            for match in virtual_stack:
                file = match['file']
                if file not in temp_docs:
                    temp_docs[file] = {
                        'filename': file,
                        'description': file_books[file].description,
                        'matches': []
                    }
                temp_docs[file]['matches'].append(match)

            documentation = generate_combined_documentation(temp_docs.values())
            batch_data = {
                'query': query,
                'documentation': documentation,
                'additional_instructions': additional_instructions
            }
            batches_to_process.append(batch_data)

        send_progress("Génération de la réponse par lot...")
        with ThreadPoolExecutor() as executor:
            future_to_batch = {
                executor.submit(
                    process_batch,
                    batch_data,
                    api_key,
                    model_type_for_response
                ): batch_data for batch_data in batches_to_process
            }
            for future in as_completed(future_to_batch):
                batch_data = future_to_batch[future]
                try:
                    response = future.result()
                    if response:
                        partial_responses.append(response)
                        logging.info("Partial response received")
                except Exception as exc:
                    logging.error(f"Batch generated an exception: {exc}")

        send_progress("Fusion des réponses partielles...")
        final_response = merge_responses(app,partial_responses, query, max_tokens=14000)

        response_data = {
            "LLMresponse": final_response,
            "documents": list(documents.values()),
            "matches": {
                "all_matches": all_matches,
            }
        }

        send_progress("Sauvegarde de la réponse dans la base de données...")
        query_id = query_service.save_query(query, vector_to_compare, response_data)
        response_data["_id"] = query_id

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
        
def process_batch(batch_data, api_key, model_type):
    """
    Traite un lot de données et génère une réponse via le modèle de langage.

    Args:
        batch_data: Dictionnaire contenant les données du lot
        api_key: Clé API pour le modèle
        model_type: Type de modèle à utiliser

    Returns:
        str: Réponse générée par le modèle
    """
    try:
        query = batch_data['query']
        documentation = batch_data['documentation']
        additional_instructions = batch_data['additional_instructions']
        return generate_ai_response(
            query,
            documentation,
            additional_instructions,
            api_key=api_key,
            model_type=model_type
        )
    except Exception as e:
        logging.error(f"Error in processing batch: {e}")
        return None