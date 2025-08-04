"""
Module d'encodage et d'extraction de contenu des documents PDF pour l'application RAG API.

Ce module fournit des fonctions pour extraire, traiter et encoder le contenu des
documents PDF, incluant le texte et les images. Il génère des descriptions 
hiérarchiques du contenu, corrige le texte extrait par OCR, et traite les images
pour en extraire des descriptions textuelles.
"""
from .models.files_book import FilesBook
from .utils.text_utils import del_pages_number
from .utils.file_utils import save_processed_data, load_partial_data, save_partial_data, remove_partial_data
from .utils.ai_utils import correct_ocr_text, generate_overall_description
from .models.vision_model import PixtralModel

import fitz  # PyMuPDF
import logging
import time
import os
import tempfile

def extract_images_from_page(doc, page, temp_dir):
    """
    Extrait les images d'une page PDF et les sauvegarde dans un répertoire temporaire.

    Args:
        doc (fitz.Document): Document PDF source
        page (fitz.Page): Page du document à traiter
        temp_dir (str): Chemin du répertoire temporaire pour sauvegarder les images

    Returns:
        list: Liste des chemins des images extraites

    Note:
        Les images sont converties en RGB si nécessaire et sauvegardées au format PNG.
        Les ressources sont libérées après traitement.
    """
    image_list = page.get_images(full=True)
    images = []
    for img_index, img in enumerate(image_list):
        xref = img[0]
        try:
            pix = fitz.Pixmap(doc, xref)
            if pix.n < 5:  # GRAY ou RGB
                image_ext = "png"
                image_path = os.path.join(temp_dir, f"extracted_image_{page.number + 1}_{img_index}.{image_ext}")
                pix.save(image_path)
            else:  # CMYK ou autre, convertir en RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)
                image_ext = "png"
                image_path = os.path.join(temp_dir, f"extracted_image_{page.number + 1}_{img_index}.{image_ext}")
                pix.save(image_path)
            images.append(image_path)
            logging.debug(f"Image sauvegardée à '{image_path}'.")
            pix = None  # Libérer les ressources
        except Exception as e:
            logging.error(f"Erreur lors de l'extraction de l'image xref {xref} à la page {page.number + 1}: {e}")
    return images

def encode_pdf(app, pdf_path, db_path, file_name, begin, end, illustration):
    """
    Traite un document PDF pour en extraire le contenu et les images, générer des descriptions
    et sauvegarder les résultats.

    Args:
        app (Flask): Instance de l'application Flask
        pdf_path (str): Chemin vers le fichier PDF à traiter
        db_path (str): Chemin où sauvegarder les données traitées
        file_name (str): Nom du fichier PDF
        begin (int): Numéro de la première page à traiter
        end (int): Numéro de la dernière page à traiter
        illustration (bool): Si True, traite également les images du PDF

    Note:
        - Utilise un répertoire temporaire pour le traitement des images
        - Sauvegarde des données partielles pendant le traitement pour permettre la reprise
        - Génère des descriptions textuelles des images si illustration=True
        - Corrige le texte OCR des pages
        - Génère une hiérarchie de descriptions du contenu
    """
    pixtral_model = PixtralModel(api_key=app.config['MISTRAL_KEY'], model_name="pixtral-large-latest")
    start_time = time.time()
    logging.info(f"Début du traitement du PDF '{file_name}'.")
    logging.info(f"illustration: {illustration}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        logging.debug(f"Répertoire temporaire créé à '{temp_dir}'.")
        try:
            with app.app_context():
                partial_file = f"{db_path}.partial"
                partial_data = load_partial_data(partial_file)
                if partial_data:
                    logging.info(f"Fichier partiel trouvé pour '{file_name}'. Reprise du traitement.")
                    book = partial_data
                else:
                    logging.info(f"Aucun fichier partiel trouvé pour '{file_name}'. Début d'un nouveau traitement.")
                    book = FilesBook(file_name=file_name)

                logging.info(f"Ouvrir le PDF '{pdf_path}'.")
                doc = fitz.open(pdf_path)
                total_pages = end - begin + 1
                logging.info(f"Nombre total de pages à traiter: {total_pages} (de {begin} à {end}).")

                corrected_pages = []
                for page_num in range(begin - 1, end):
                    page = doc[page_num]
                    page_text = page.get_text()
                    logging.info(f"Correction OCR de la page {page_num + 1}")

                    corrected_text = correct_ocr_text(page_text, app)

                    if illustration:
                        images = extract_images_from_page(doc, page, temp_dir)
                        if images:
                            for image_path in images:
                                try:
                                    logging.debug(f"Traitement de l'image '{image_path}'.")
                                    image_description = pixtral_model.generate_response(image_path, corrected_text)
                                    corrected_text += f"\n\n### Description des illustrations\n{image_description}"
                                except Exception as e:
                                    logging.error(f"Erreur lors de la génération de la description de l'image '{image_path}': {e}")

                    corrected_pages.append({
                        "pageNumber": page_num + 1,
                        "text": corrected_text
                    })

                if not book.descriptions:
                    logging.info("Génération de l'arbre de descriptions...")
                    book.description, book.descriptions, book.descriptions_vectorized = generate_overall_description(
                        corrected_pages,
                        app.model,
                        partial_file=partial_file,
                        book=book
                    )
                    logging.info("Arbre de descriptions généré avec succès.")

                save_processed_data(db_path, book)
                logging.info(f"Fichier PDF '{file_name}' traité avec succès.")

                remove_partial_data(partial_file)
                logging.debug(f"Fichier partiel '{partial_file}' supprimé.")

        except Exception as e:
            logging.error(f"Erreur lors du traitement du PDF '{file_name}': {e}")
            logging.exception("Détails de l'erreur :")
            raise
        finally:
            elapsed_time = time.time() - start_time
            logging.info(f"Temps total de traitement pour '{file_name}': {elapsed_time:.2f} secondes.")


def process_query_simple(app, question, files, max_pages=20):
    """
    Version simplifiée de process_query pour les endpoints UXMCP.
    Retourne directement le résultat sans streaming.
    
    Args:
        app: Application Flask avec configuration
        question (str): Question à poser
        files (list): Liste des chemins de fichiers PDF
        max_pages (int): Nombre maximum de pages à analyser
        
    Returns:
        dict: Résultat avec answer et matches
    """
    try:
        from .pdf_aiProcessing import process_query
        
        # Appeler la fonction process_query existante sans callback de progress
        result = process_query(
            app,
            question,
            files,
            new_generate=False,  # Utiliser le cache si disponible
            additional_instructions="",
            max_page=str(max_pages),
            progress_callback=None,  # Pas de callback pour la version simple
            mode_infinity=False,  # Pas de mode infinity pour la simplicité
            add_section=True
        )
        
        # Reformater le résultat pour la version simple
        if result and 'LLMresponse' in result:
            return {
                'answer': result['LLMresponse'],
                'matches': result.get('matches', {}),
                'documents': result.get('documents', [])
            }
        else:
            return {
                'answer': 'Aucune réponse générée.',
                'matches': {},
                'documents': []
            }
            
    except Exception as e:
        logging.error(f"Erreur dans process_query_simple: {e}")
        return {
            'answer': f'Erreur lors du traitement: {str(e)}',
            'matches': {},
            'documents': []
        }


def get_relevant_sources_simple(app, query, files=None, k=5, max_pages=30, auto_select_books=2):
    """
    Récupère les sources les plus pertinentes pour une requête sans générer de réponse.
    Peut sélectionner automatiquement les livres les plus pertinents.
    
    Args:
        app: Application Flask avec configuration
        query (str): Question à analyser
        files (list, optional): Liste des chemins PDF. Si None, sélection automatique
        k (int): Nombre de sources à retourner (max 20)
        max_pages (int): Nombre max de pages par livre (max 100)
        auto_select_books (int): Nombre de livres à sélectionner automatiquement (max 5)
        
    Returns:
        dict: Résultat avec sources et métadonnées
    """
    import time
    start_time = time.time()
    
    try:
        from .utils.pdfQuery_utils import (
            extract_keywords, vectorize_user_query, load_and_score_files,
            filter_matches_by_score_and_page, llm_filter_matches
        )
        from .services.book_service import BookService
        
        # Limiter les paramètres
        k = min(max(k, 1), 20)
        max_pages = min(max(max_pages, 5), 100)
        auto_select_books = min(max(auto_select_books, 1), 5)
        
        device = app['config']['device']
        model = app['model']
        api_key = app['config']['API_KEY']
        model_type_for_filter = app['config']['AI_MODEL_TYPE']
        
        book_service = BookService()
        selected_books = []
        mode = "manual"
        
        # Étape 1: Sélection des livres
        if files is None or len(files) == 0:
            mode = "automatic"
            logging.info(f"Sélection automatique de livres pour: '{query}'")
            
            # Recherche vectorielle des livres pertinents
            search_results = book_service.search_books_by_description(
                query, top_k=auto_select_books, threshold=0.3
            )
            
            if not search_results:
                return {
                    'query': query,
                    'mode': mode,
                    'books_selected': [],
                    'sources': [],
                    'processing_info': {
                        'error': 'Aucun livre pertinent trouvé',
                        'execution_time': time.time() - start_time
                    }
                }
            
            # Préparer les livres sélectionnés
            files = []
            for result in search_results:
                if result.get('pdf_path'):
                    files.append(result['pdf_path'])
                    selected_books.append({
                        'title': result.get('title', ''),
                        'author': result.get('author', ''),
                        'file_path': result.get('pdf_path', ''),
                        'similarity_score': round(result.get('similarity_score', 0), 3),
                        'selection_reason': 'Sélection automatique basée sur la similarité sémantique'
                    })
                    
            logging.info(f"Livres sélectionnés automatiquement: {[b['title'] for b in selected_books]}")
        else:
            mode = "manual"
            # Mode manuel : utiliser les fichiers fournis
            for file_path in files:
                book_data = book_service.get_book_by_filename(file_path)
                if book_data:
                    selected_books.append({
                        'title': book_data.get('title', ''),
                        'author': book_data.get('author', ''),
                        'file_path': file_path,
                        'similarity_score': 1.0,
                        'selection_reason': 'Spécifié manuellement par l\'utilisateur'
                    })
        
        if not files:
            return {
                'query': query,
                'mode': mode,
                'books_selected': selected_books,
                'sources': [],
                'processing_info': {
                    'error': 'Aucun fichier à analyser',
                    'execution_time': time.time() - start_time
                }
            }
        
        # Étape 2: Extraction des sources (pipeline RAG simplifié)
        logging.info(f"Extraction des sources pour {len(files)} fichier(s)")
        
        # Extraction des mots-clés
        most_words = extract_keywords(query, lambda msg: logging.debug(f"Keywords: {msg}"))
        
        # Vectorisation de la requête
        vector_to_compare = vectorize_user_query(query, model, lambda msg: logging.debug(f"Vectorization: {msg}"))
        
        # Chargement et scoring des fichiers
        leaf_matches, tree_matches, processed_file_books = load_and_score_files(
            app, files, vector_to_compare, most_words, 
            lambda msg: logging.debug(f"File processing: {msg}")
        )
        
        # Filtrage initial par score et page
        initial_matches = filter_matches_by_score_and_page(leaf_matches, tree_matches, max_pages)
        
        # Filtrage LLM pour la pertinence
        all_matches = llm_filter_matches(
            initial_matches, query, api_key, model_type_for_filter,
            lambda msg: logging.debug(f"LLM filtering: {msg}")
        )
        
        # Limiter aux k meilleures sources
        top_sources = all_matches[:k] if all_matches else []
        
        # Formater les sources pour la réponse
        formatted_sources = []
        for match in top_sources:
            formatted_sources.append({
                'text': match.get('text', ''),
                'file': match.get('file', ''),
                'page': match.get('page_num', 0),
                'page_range': match.get('page_range', ''),
                'relevance_score': round(match.get('score', 0), 3),
                'match_type': 'leaf' if match in leaf_matches else 'tree'
            })
        
        execution_time = time.time() - start_time
        
        return {
            'query': query,
            'mode': mode,
            'books_selected': selected_books,
            'sources': formatted_sources,
            'processing_info': {
                'books_analyzed': len(files),
                'total_matches_before_filter': len(initial_matches),
                'total_matches_after_filter': len(all_matches),
                'sources_returned': len(formatted_sources),
                'keywords_extracted': most_words[:5] if most_words else [],
                'execution_time': round(execution_time, 2),
                'auto_selection_used': mode == "automatic"
            }
        }
        
    except Exception as e:
        logging.error(f"Erreur dans get_relevant_sources_simple: {e}")
        return {
            'query': query,
            'mode': mode,
            'books_selected': selected_books,
            'sources': [],
            'processing_info': {
                'error': str(e),
                'execution_time': time.time() - start_time
            }
        }