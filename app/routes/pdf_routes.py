"""
Routes pour le traitement et l'analyse des documents PDF.

Ce module gère toutes les routes liées au traitement des PDF, incluant :
- L'analyse de documents
- La génération de descriptions
- Le calcul de similarités
- La gestion des images de pages
"""

import json
from flask import Blueprint, Response, jsonify, request, current_app, send_from_directory, abort, stream_with_context
import logging
import os
from threading import Thread
from queue import Queue
from app.utils.auth_utils import token_required
from app.utils.images_utils import convert_pdf_page_to_image
from app.utils.vector_utils import compare_query_to_descriptions, serialize_tensor
from app.utils.file_utils import load_processed_data, save_processed_data
from app.utils.ai_utils import reduceTextForDescriptions
from app.pdf_aiProcessing import process_query
from app.pdf_aiEncode import encode_pdf
from app.services import BookService
from app.config import extract_config

# Création du Blueprint
pdf_bp = Blueprint('pdf', __name__)
book_service = BookService()

def run_process_query(app,query, files, new_generate, additional_instructions, max_page, queue):
    def progress_callback(msg):
        # Ajouter le message de progression dans la queue
        queue.put(("progress", msg))

    # Appel de votre process_query
    result = process_query(
        app,
        query,
        files,
        new_generate,
        additional_instructions=additional_instructions,
        max_page=max_page,
        progress_callback=progress_callback
    )

    # Une fois terminé, mettre la réponse finale dans la queue
    queue.put(("final", result))

@pdf_bp.route('/process-sse', methods=['GET'])
def process_sse():
    query = request.args.get("query")
    max_page = request.args.get("max_page", "30")
    new_generate = request.args.get("new", "")
    additional_instructions = request.args.get("additional_instructions", "")
    files = request.args.getlist("files")

    q = Queue()

    # Lancer process_query dans un thread séparé
    t = Thread(target=run_process_query, args=(extract_config(current_app),query, files, new_generate, additional_instructions, max_page, q))
    t.start()

    def event_stream():
        # Tant que le thread n'a pas terminé, on lit la queue
        while True:
            item = q.get()  # On attend qu'un message arrive
            if item is None:
                # Si on reçoit None, on arrête le streaming
                break

            msg_type, content = item
            if msg_type == "progress":
                # Envoyer le message de progression immédiatement
                yield f"data: {content}\n\n"
            elif msg_type == "final":
                # Envoyer la réponse finale (en JSON)
                yield f"data: {json.dumps(content)}\n\n"
                break

    return Response(stream_with_context(event_stream()), mimetype='text/event-stream')

@pdf_bp.route('/images/<filename>')
def serve_image(filename):
    """
    Sert une image depuis le répertoire des images.
    
    Args:
        filename (str): Nom du fichier image
        
    Returns:
        File: Fichier image demandé
    """
    logging.info(f"Serving image: {filename}")
    return send_from_directory(current_app.config['IMAGE_FOLDER'], filename)

@pdf_bp.route('/<path:subpath>/<filename>')
def serve_pdf(subpath, filename):
    """
    Sert un fichier PDF depuis le répertoire des PDFs.
    
    Args:
        subpath (str): Sous-chemin dans le répertoire PDF
        filename (str): Nom du fichier PDF
        
    Returns:
        File: Fichier PDF demandé
        404: Si le fichier n'existe pas
    """
    # Essayer d'abord le chemin direct
    full_path = os.path.join(current_app.config['PDF_FOLDER'], subpath, filename)
    if os.path.exists(full_path) and os.path.commonpath([full_path, current_app.config['PDF_FOLDER']]) == current_app.config['PDF_FOLDER']:
        return send_from_directory(current_app.config['PDF_FOLDER'], os.path.join(subpath, filename))
    
    # Si non trouvé, rechercher dans tous les sous-répertoires
    for root, dirs, files in os.walk(current_app.config['PDF_FOLDER']):
        if filename in files:
            relative_path = os.path.relpath(root, current_app.config['PDF_FOLDER'])
            file_path = os.path.join(relative_path, filename)
            if relative_path == '.':
                file_path = filename
            return send_from_directory(current_app.config['PDF_FOLDER'], file_path)
    
    abort(404)

@pdf_bp.route('/title/<title>/descriptions', methods=['GET'])
@token_required
def get_descriptions_by_title(current_user, title):
    """
    Récupère les descriptions d'un livre par son titre.
    
    Args:
        current_user (dict): Informations sur l'utilisateur courant
        title (str): Titre du livre
        
    Returns:
        JSON: Liste des descriptions du livre
        404: Si le livre n'est pas trouvé
        500: En cas d'erreur serveur
    """
    try:
        db_book = book_service.get_book_by_title(title)
        if not db_book:
            return jsonify({"error": "Livre non trouvé"}), 404

        db_path = db_book['pdf_path']
        if not db_path:
            return jsonify({"error": "Chemin du fichier non trouvé"}), 404

        files_book = load_processed_data(current_app, db_path)
        if not files_book:
            return jsonify({"error": "Impossible de charger les données traitées"}), 500

        if not files_book.descriptions:
            return jsonify({"error": "Descriptions non trouvées"}), 404

        return jsonify({"descriptions": files_book.descriptions}), 200

    except Exception as e:
        logging.error(f"Erreur lors de la récupération des descriptions : {e}")
        return jsonify({"error": str(e)}), 500

@pdf_bp.route('/title/<title>/similarity', methods=['POST'])
@token_required
def get_similarity_by_title(current_user, title):
    """
    Calcule la similarité entre une requête et les descriptions d'un livre.
    
    Args:
        current_user (dict): Informations sur l'utilisateur courant
        title (str): Titre du livre
        
    Returns:
        JSON: Scores de similarité calculés
        400: Si la requête est manquante
        404: Si le livre n'est pas trouvé
        500: En cas d'erreur serveur
    """
    try:
        query = request.json.get('query')
        if not query:
            return jsonify({"error": "Query is required"}), 400

        db_book = book_service.get_book_by_title(title)
        if not db_book:
            return jsonify({"error": "Book not found"}), 404

        db_path = db_book['db_path']
        if not db_path:
            return jsonify({"error": "DB path not found"}), 404

        if db_path.endswith('.db'):
            db_path = db_path[:-3]

        files_book = load_processed_data(current_app, db_path)
        if not files_book:
            return jsonify({"error": "Unable to load processed data"}), 500

        if not files_book.descriptions:
            return jsonify({"error": "Descriptions not found"}), 404

        if not files_book.descriptions_vectorized:
            logging.info("Computing description vectors...")
            descriptions_vectorized = []
            for level in files_book.descriptions:
                level_vectors = []
                for desc in level:
                    embedding = current_app.model.encode(desc, convert_to_tensor=True, normalize_embeddings=True)
                    level_vectors.append(serialize_tensor(embedding))
                descriptions_vectorized.append(level_vectors)
            files_book.descriptions_vectorized = descriptions_vectorized
            save_processed_data(db_path, files_book)
            logging.info("Description vectors computed and saved")

        similarities = compare_query_to_descriptions(
            query,
            files_book.descriptions,
            files_book.descriptions_vectorized,
            current_app.model,
            current_app.config['device']
        )

        return jsonify({"similarities": similarities}), 200

    except Exception as e:
        logging.error(f"Error in similarity calculation: {e}")
        return jsonify({"error": str(e)}), 500

@pdf_bp.route("/process", methods=["POST"])
@token_required
def encode_pdf_route(current_user):
    """
    Traite une requête d'analyse de documents PDF.
    
    Args:
        current_user (dict): Informations sur l'utilisateur courant
        
    Returns:
        JSON: Résultats de l'analyse
        400: Si les paramètres requis sont manquants
        500: En cas d'erreur serveur
    """
    try:
        data = request.json
        query = data.get("query")
        files = data.get("files")
        max_page = data.get("max_page")
        new_generate = data.get("new", "")
        additional_instructions = data.get("additional_instructions", "")

        if not query or not files:
            return jsonify({"error": "Query and files are required"}), 400

        if not isinstance(files, list):
            return jsonify({"error": "Files should be a list"}), 400

        response_data = process_query(
            current_app, 
            query, 
            files, 
            new_generate, 
            additional_instructions, 
            max_page
        )
        return response_data

    except Exception as e:
        logging.error(f"Error in process_pdf_route: {e}")
        return jsonify({"error": str(e)}), 500

@pdf_bp.route('/generate-preview', methods=['POST'])
@token_required
def generate_pdf_preview(current_user):
    """
    Génère une prévisualisation d'une page de PDF.
    
    Args:
        current_user (dict): Informations sur l'utilisateur courant
        
    Returns:
        JSON: Chemin de l'image générée
        400: Si les paramètres sont invalides
        500: En cas d'erreur
    """
    try:
        data = request.json
        pdf_path = data.get('pdf_path')
        page_number = data.get('page_number', 0)
        max_width = data.get('max_width', 800)

        if not pdf_path:
            return jsonify({"error": "PDF path is required"}), 400

        full_pdf_path = os.path.join(current_app.config['PDF_FOLDER'], pdf_path)
        if not os.path.exists(full_pdf_path):
            return jsonify({"error": "PDF file not found"}), 404

        image_filename, _ = convert_pdf_page_to_image(
            pdf_path=full_pdf_path,
            page_number=page_number,
            max_width=max_width,
            output_format='webp'
        )

        if not image_filename:
            return jsonify({"error": "Failed to generate preview"}), 500

        return jsonify({
            "message": "Preview generated successfully",
            "image_path": f"/pdf/images/{image_filename}"
        }), 200

    except Exception as e:
        logging.error(f"Error generating PDF preview: {e}")
        return jsonify({"error": str(e)}), 500

@pdf_bp.route('/batch-process', methods=['POST'])
@token_required
def batch_process_pdfs(current_user):
    """
    Lance le traitement par lot de plusieurs PDFs.
    
    Args:
        current_user (dict): Informations sur l'utilisateur courant
        
    Returns:
        JSON: Confirmation du lancement du traitement
        403: Si l'utilisateur n'est pas administrateur
        400: Si les paramètres sont invalides
    """
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Admin privileges required'}), 403

    try:
        data = request.json
        pdf_files = data.get('pdf_files', [])
        
        if not pdf_files:
            return jsonify({"error": "No PDF files specified"}), 400

        for pdf_info in pdf_files:
            pdf_path = pdf_info.get('path')
            db_path = pdf_info.get('db_path')
            filename = pdf_info.get('filename')
            begin = pdf_info.get('begin', 0)
            end = pdf_info.get('end', 0)
            illustration = pdf_info.get('illustration', False)

            if not all([pdf_path, db_path, filename]):
                continue

            thread = Thread(target=encode_pdf, args=(
                current_app._get_current_object(),
                pdf_path,
                db_path,
                filename,
                begin,
                end,
                illustration
            ))
            thread.start()

        return jsonify({
            "message": "Batch processing started",
            "files_count": len(pdf_files)
        }), 202

    except Exception as e:
        logging.error(f"Error in batch PDF processing: {e}")
        return jsonify({"error": str(e)}), 500
    
@pdf_bp.route("/pdfai", methods=["POST"])
@token_required
def pdfai_post(current_user):
    """
    Traite une requête d'analyse de documents PDF.
    
    Args:
        current_user (dict): Informations sur l'utilisateur courant
        
    Returns:
        JSON: Résultats de l'analyse
        400: Si les paramètres requis sont manquants
        500: En cas d'erreur serveur
    """
    try:
        data = request.json
        query = data.get("query")
        files = data.get("files")
        max_page = data.get("max_page")
        new_generate = data.get("new", "")
        additional_instructions = data.get("additional_instructions", "")

        if not query or not files:
            return jsonify({"error": "Query and files are required"}), 400

        if not isinstance(files, list):
            return jsonify({"error": "Files should be a list"}), 400

        response_data = process_query(current_app, query, files, new_generate, additional_instructions, max_page)
        return response_data

    except Exception as e:
        logging.error(f"Error in pdfai_post: {e}")
        return {"error": str(e)}, 500
    
@pdf_bp.route('/', methods=['POST'])
@token_required
def create_book_route(current_user):
    """
    Crée un nouveau livre dans la base de données.
    
    Args:
        current_user (dict): Informations sur l'utilisateur courant
        
    Returns:
        JSON: ID du livre créé et message de confirmation
        400: Si le fichier PDF est manquant
        403: Si l'utilisateur n'est pas administrateur
        500: En cas d'erreur serveur
    """
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Admin privileges required'}), 403
    try:
        data = request.form.to_dict()
        data['proprietary'] = current_user['username']

        logging.info(f"Données reçues pour la création du livre : {data}")

        # Gestion de l'image de couverture
        if 'cover_image' in request.files:
            cover_image = request.files['cover_image']
            filename = cover_image.filename
            cover_image_path = os.path.join(current_app.config['IMAGE_FOLDER'], filename)
            cover_image.save(cover_image_path)
            data['cover_image'] = filename

        # Gestion du fichier PDF
        if 'pdf_file' not in request.files:
            return jsonify({"error": "Fichier PDF requis"}), 400

        pdf_file = request.files['pdf_file']
        pdf_filename = pdf_file.filename
        directory = data.get('directory', 'default')

        # Création des répertoires nécessaires
        pdf_directory = os.path.join(current_app.config['PDF_FOLDER'], directory)
        if not os.path.exists(pdf_directory):
            os.makedirs(pdf_directory)

        pdf_path = os.path.join(pdf_directory, pdf_filename)
        pdf_file.save(pdf_path)

        db_path = os.path.join(current_app.config['FOLDER_PATH'], directory, pdf_filename)
        illustration_value = data.get('illustration', 'false').lower() == 'true'
        # Création du livre dans la base de données
        book_id = book_service.create_book({
            'title': data.get('title'),
            'author': data.get('author'),
            'edition': data.get('edition'),
            'proprietary': data.get('proprietary'),
            'cover_image': data.get('cover_image'),
            'category': data.get('category'),
            'subcategory': data.get('subcategory'),
            'directory': directory,
            'begin': int(data.get('begin', 0)),
            'illustration': illustration_value,
            'end': int(data.get('end', 0)),
            'pdf_path': os.path.join(directory, pdf_filename),
            'db_path': os.path.join(directory, pdf_filename + ".db"),
            'metadata': data.get('metadata', {})
        })

        if not book_id:
            return jsonify({"error": "Failed to create book"}), 500

        # Lancement du traitement PDF en arrière-plan
        thread = Thread(target=encode_pdf, args=(
            current_app._get_current_object(),
            pdf_path,
            db_path,
            pdf_filename,
            int(data.get('begin', 0)),
            int(data.get('end', 0)),
            illustration_value
        ))
        thread.start()

        return jsonify({
            "message": "Book created successfully",
            "book_id": book_id
        }), 201

    except Exception as e:
        logging.error(f"Error creating book: {e}")
        return jsonify({"error": str(e)}), 500