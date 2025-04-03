"""
Module d'utilitaires pour les requêtes sur les documents PDF.

Ce module fournit des fonctions pour l'extraction, la vectorisation, et l'analyse
de requêtes textuelles sur des documents PDF préalablement traités. Il gère le 
pipeline complet de recherche, incluant l'extraction de mots-clés, la vectorisation,
la recherche dans le cache, le chargement et le scoring des fichiers, le filtrage des 
correspondances, et la génération de réponses via des modèles d'IA.

Functions:
    extract_keywords: Extrait les mots-clés importants d'une requête.
    vectorize_user_query: Vectorise une requête utilisateur.
    check_cache: Vérifie si une réponse existe dans le cache.
    load_and_score_files: Charge les fichiers et évalue leur pertinence.
    filter_matches_by_score_and_page: Filtre les correspondances par score et numéro de page.
    llm_filter_matches: Filtre les correspondances à l'aide d'un modèle de langage.
    prepare_batches_for_llm: Prépare les lots pour le traitement par le LLM.
    process_batch: Traite un lot de données pour générer une réponse partielle.
    generate_partial_responses: Génère des réponses partielles en parallèle.
    merge_all_responses: Fusionne toutes les réponses partielles.
    save_response_to_db: Sauvegarde la réponse dans la base de données.
"""

import logging
import torch
from sentence_transformers import util
from concurrent.futures import ThreadPoolExecutor, as_completed
from .text_utils import contain_key, search_upper_words, vectorize_query
from .ai_utils import (
    estimate_tokens,
    generate_ai_response,
    generate_combined_documentation,
    merge_responses,
    llm_filter_matches,
)
from .file_utils import load_processed_data

def extract_keywords(query, send_progress):
    """
    Extrait les mots-clés importants d'une requête utilisateur.
    
    Cette fonction analyse la requête pour en extraire les mots les plus significatifs,
    qui seront utilisés pour filtrer les documents pertinents.
    
    Args:
        query (str): La requête utilisateur à analyser.
        send_progress (callable): Fonction de callback pour signaler la progression.
        
    Returns:
        list: Liste des mots-clés extraits de la requête.
    """
    send_progress("Extraction des mots-clés...")
    most_words = search_upper_words(query)
    logging.info(f"Extracted keywords: {most_words}")
    return most_words

def vectorize_user_query(query, model, send_progress):
    """
    Vectorise une requête utilisateur à l'aide d'un modèle d'embedding.
    
    Transforme la requête textuelle en un vecteur numérique pour permettre
    la comparaison avec les vecteurs des documents.
    
    Args:
        query (str): La requête utilisateur à vectoriser.
        model: Le modèle d'embedding à utiliser pour la vectorisation.
        send_progress (callable): Fonction de callback pour signaler la progression.
        
    Returns:
        torch.Tensor: Vecteur représentant la requête utilisateur.
    """
    send_progress("Vectorisation de la requête...")
    vector_to_compare = vectorize_query(query, model)
    logging.info("Query vectorization completed")
    return vector_to_compare

def check_cache(query, most_words, vector_to_compare, query_service, device, new_generate, send_progress):
    """
    Vérifie si une réponse similaire existe déjà dans le cache.
    
    Cette fonction recherche dans la base de données des requêtes précédentes
    une requête similaire à celle soumise par l'utilisateur, en utilisant
    à la fois les mots-clés et la similarité vectorielle.
    
    Args:
        query (str): La requête utilisateur.
        most_words (list): Liste des mots-clés extraits de la requête.
        vector_to_compare (torch.Tensor): Vecteur de la requête utilisateur.
        query_service: Service de gestion des requêtes en base de données.
        device (str): Dispositif de calcul à utiliser (CPU/GPU).
        new_generate (str): Si "new", ignore le cache et force une nouvelle génération.
        send_progress (callable): Fonction de callback pour signaler la progression.
        
    Returns:
        dict or None: La réponse mise en cache si trouvée, None sinon.
    """
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
    return None

def load_and_score_files(app, files, vector_to_compare, most_words, send_progress):
    leaf_matches = []
    tree_matches = []
    file_books = {}
    device = app['config']['device']

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

    return leaf_matches, tree_matches, file_books

def filter_matches_by_score_and_page(leaf_matches, tree_matches, max_page):
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
    return all_matches[:MAX_MATCHES]

# Suppression du wrapper et import direct de la fonction pour éviter la duplication

def prepare_batches_for_llm(query, all_matches, file_books, send_progress):
    send_progress("Préparation des lots pour la génération de la réponse...")
    main_stack = all_matches.copy()
    virtual_stack = []
    batches_to_process = []

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
                'additional_instructions': ""  # Instructions supplémentaires vides pour les lots initiaux
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
            'additional_instructions': ""  # Instructions supplémentaires vides pour les lots initiaux
        }
        batches_to_process.append(batch_data)

    return batches_to_process

def process_batch(batch_data, api_key, model_type):
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

def generate_partial_responses(batches_to_process, api_key, model_type_for_response, send_progress):
    send_progress("Génération de la réponse par lot...")
    partial_responses = []
    total_batches = len(batches_to_process)
    completed_count = 0

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
            try:
                response = future.result()
                completed_count += 1
                if response:
                    partial_responses.append(response)
                    logging.info("Partial response received")
                    # Envoi de la progression détaillée
                    send_progress(f"Réception de la réponse partielle {completed_count}/{total_batches}...")
            except Exception as exc:
                logging.error(f"Batch generated an exception: {exc}")
                # On compte tout de même cette tentative de traitement comme terminée
                # même si elle a échoué, afin de ne pas fausser le décompte
                send_progress(f"Erreur lors du traitement d'une réponse partielle {completed_count+1}/{total_batches}.")
                completed_count += 1

    return partial_responses

def merge_all_responses(app, partial_responses, query, additional_instructions="", send_progress=None, add_section=True):
    logging.info("Fusion des réponses partielles...")
    # Ajout du paramètre send_progress dans l'appel à merge_responses
    final_response = merge_responses(
        app, 
        partial_responses, 
        query, 
        max_tokens=14000, 
        additional_instructions=additional_instructions,
        send_progress=send_progress,
        add_section=add_section
    )
    return final_response

def save_response_to_db(query_service, query, vector_to_compare, response_data, send_progress):
    send_progress("Sauvegarde de la réponse dans la base de données...")
    query_id = query_service.save_query(query, vector_to_compare, response_data)
    response_data["_id"] = query_id
    return response_data