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

def process_query(app, query, files, new_generate, additional_instructions="", max_page="30"):
    """
    Traite une requête utilisateur en recherchant dans les documents PDF et génère une réponse.

    Args:
        app: Instance de l'application Flask
        query: Requête de l'utilisateur
        files: Liste des fichiers à analyser
        new_generate: Indicateur pour forcer une nouvelle génération
        additional_instructions: Instructions supplémentaires pour le modèle
        max_page: Nombre maximum de pages à traiter

    Returns:
        dict: Réponse structurée contenant les résultats de la recherche
    """
    try:
        partial_responses = []
        batches_to_process = []
        
        logging.info("=" * 50)
        logging.info("STARTING QUERY PROCESSING")
        logging.info(f"Query: {query}")
        logging.info(f"Files to analyze: {files}")
        logging.info(f"Force new generation: {new_generate}")
        logging.info(f"Additional instructions: {additional_instructions}")
        logging.info("=" * 50)

        start_time = time.time()
        device = app.config['device']
        model = app.model

        api_key = app.config['API_KEY']
        model_type_for_response = app.config['AI_MODEL_TYPE_FOR_REPONSE']
        model_type_for_filter= app.config['AI_MODEL_TYPE']

        # Extraction des mots-clés et vectorisation de la requête
        most_words = search_upper_words(query)
        logging.info(f"Extracted keywords: {most_words}")

        vector_to_compare = vectorize_query(query, model)
        logging.info("Query vectorization completed")

        # Vérification du cache sauf si nouvelle génération forcée
        if new_generate != "new":
            logging.info("Searching in cache...")
            cached_response = query_service.search_similar_query(
                query, 
                most_words, 
                vector_to_compare, 
                device
            )
            if cached_response:
                logging.info("Response found in cache")
                return cached_response['response']
            logging.info("No cached response found")

        # Initialisation des collections
        leaf_matches = []
        tree_matches = []
        documents = {}
        file_books = {}

        # Traitement de chaque fichier
        for file in files:
            logging.info(f"\nProcessing file: {file}")
            loaded_book = load_processed_data(app, file)
            if loaded_book is None:
                logging.warning(f"Unable to load data for: {file}")
                continue

            logging.info(f"Data loaded successfully for: {file}")

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

        # Tri par score et numéro de page
        all_matches.sort(key=lambda x: (-x['score'], x['page_num']))

        # Filtrage initial par score
        MAX_MATCHES = int(max_page)
        initial_matches = all_matches[:MAX_MATCHES]

        # Filtrage par LLM
        logging.info(f"Début du filtrage LLM sur {len(initial_matches)} passages")
        filtered_matches = []

        for match in initial_matches:
            is_relevant = filter_match_by_llm(
                match, 
                query, 
                api_key, 
                model_type_for_filter
            )
            
            if is_relevant:
                filtered_matches.append(match)
                logging.info(f"Page {match['page_num']} conservée (score: {match['score']:.3f})")
            else:
                logging.info(f"Page {match['page_num']} retirée (score: {match['score']:.3f})")

        all_matches = filtered_matches

        all_matches.sort(key=lambda x: x['page_num'])

        if not all_matches:
            logging.warning("No matches found after filtering")
            return {
                "LLMresponse": "Aucune correspondance pertinente n'a été trouvée dans les documents fournis.",
                "documents": [],
                "matches": {
                    "leaf_matches": [],
                    "tree_matches": []
                }
            }

        logging.info(f"\nStatistics of retained matches:")
        logging.info(f"- Total matches: {len(all_matches)}")
        logging.info(f"- Highest score: {all_matches[0]['score']:.3f}")
        logging.info(f"- Lowest score: {all_matches[-1]['score']:.3f}")
        logging.info(f"- First page: {all_matches[0]['page_num']}")
        logging.info(f"- Last page: {all_matches[-1]['page_num']}")

        # Préparation des lots pour le traitement parallèle
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

        # Traitement du dernier lot
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

        logging.info("\nPreparing to process batches in parallel")

        # Traitement parallèle des lots
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

        # Fusion des réponses partielles
        logging.info(f"Merging {len(partial_responses)} partial responses")
        final_response = merge_responses(partial_responses, query, max_tokens=14000)

        # Construction de la réponse finale
        response_data = {
            "LLMresponse": final_response,
            "documents": list(documents.values()),
            "matches": {
                "leaf_matches": leaf_matches,
                "tree_matches": tree_matches
            }
        }

        # Sauvegarde de la réponse dans la base de données
        logging.info("\nSaving response to the database")
        query_id = query_service.save_query(query, vector_to_compare, response_data)
        response_data["_id"] = query_id

        execution_time = time.time() - start_time
        logging.info("=" * 50)
        logging.info("END OF QUERY PROCESSING")
        logging.info(f"Total execution time: {execution_time:.2f} seconds")
        logging.info(f"Number of batches processed: {len(batches_to_process)}")
        logging.info(f"Number of partial responses: {len(partial_responses)}")
        logging.info("=" * 50)

        return response_data

    except Exception as e:
        logging.error(f"Error in process_query: {e}")
        logging.exception("Details of the error:")
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