import logging
import os
import time
from threading import Thread
from flask import Blueprint, jsonify, request, current_app
from app.pdf_aiEncode import encode_pdf
from app.services import BookService
from app.utils.ai_utils import reduceTextForDescriptions
from app.utils.file_utils import load_processed_data, save_processed_data
from app.utils.images_utils import convert_pdf_page_to_image
from app.utils.vector_utils import compare_query_to_descriptions, serialize_tensor
from app.dto.book_dto import (
    BookCreationRequestDTO, BookUpdateRequestDTO, BookResponseDTO, 
    BookListResponseDTO, GenerateCoverRequestDTO, DescriptionGenerationRequestDTO
)
from app.dto.book_search_dto import (
    BookSearchRequestDTO, BookSearchResultDTO, BookSearchResponseDTO, EmbeddingStatsDTO
)

book_bp = Blueprint('book', __name__)
book_service = BookService()

@book_bp.route('/', methods=['POST'])
def create_book_route():
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
    try:
        form_data = request.form.to_dict()
        
        # Création du DTO pour la requête
        book_creation_request = BookCreationRequestDTO(
            title=form_data.get('title', ''),
            author=form_data.get('author', ''),
            description=form_data.get('description'),
            public=form_data.get('public', 'false').lower() == 'true'
        )
        
        # Ajout de propriétés supplémentaires spécifiques à notre implémentation
        form_data['proprietary'] = 'system'

        logging.info(f"Données reçues pour la création du livre : {form_data}")

        # Gestion de l'image de couverture
        if 'cover_image' in request.files:
            cover_image = request.files['cover_image']
            filename = cover_image.filename
            cover_image_path = os.path.join(current_app.config['IMAGE_FOLDER'], filename)
            cover_image.save(cover_image_path)
            form_data['cover_image'] = filename
            book_creation_request.cover_image = filename

        # Gestion du fichier PDF
        if 'pdf_file' not in request.files:
            return jsonify({"error": "Fichier PDF requis"}), 400

        pdf_file = request.files['pdf_file']
        pdf_filename = pdf_file.filename
        book_creation_request.filename = pdf_filename
        directory = form_data.get('directory', 'default')

        # Création des répertoires nécessaires
        pdf_directory = os.path.join(current_app.config['PDF_FOLDER'], directory)
        if not os.path.exists(pdf_directory):
            os.makedirs(pdf_directory)

        pdf_path = os.path.join(pdf_directory, pdf_filename)
        pdf_file.save(pdf_path)

        db_path = os.path.join(current_app.config['FOLDER_PATH'], directory, pdf_filename)
        illustration_value = form_data.get('illustration', 'false').lower() == 'true'
        
        # Création du livre dans la base de données
        book_data = {
            'title': book_creation_request.title,
            'author': book_creation_request.author,
            'description': book_creation_request.description,
            'edition': form_data.get('edition'),
            'proprietary': form_data.get('proprietary'),
            'cover_image': book_creation_request.cover_image,
            'category': form_data.get('category'),
            'subcategory': form_data.get('subcategory'),
            'directory': directory,
            'begin': int(form_data.get('begin', 0)),
            'illustration': illustration_value,
            'end': int(form_data.get('end', 0)),
            'pdf_path': os.path.join(directory, pdf_filename),
            'db_path': os.path.join(directory, pdf_filename + ".db"),
            'public': book_creation_request.public,
            'metadata': form_data.get('metadata', {})
        }
        
        logging.info(f"Tentative de création du livre avec les données : {book_data}")
        
        try:
            book_id = book_service.create_book(book_data)
            logging.info(f"Livre créé avec l'ID : {book_id}")
        except Exception as e:
            logging.error(f"Erreur lors de la création du livre : {e}")
            return jsonify({"error": f"Database error: {str(e)}"}), 500

        if not book_id:
            logging.error("book_service.create_book a retourné None")
            return jsonify({"error": "Failed to create book - no ID returned"}), 500

        # Génération de l'embedding si une description est fournie
        if book_creation_request.description and book_creation_request.description.strip():
            try:
                from ..utils.book_embedding_utils import generate_description_embedding
                if hasattr(current_app, 'model'):
                    embedding_data, model_name, timestamp = generate_description_embedding(
                        book_creation_request.description, current_app.model
                    )
                    if embedding_data:
                        book_service.update_book(book_id, {
                            'description_embedding': embedding_data,
                            'description_embedding_model': model_name,
                            'description_embedding_date': timestamp
                        })
                        logging.info(f"Embedding généré pour le livre {book_id}")
                    else:
                        logging.warning(f"Échec de la génération de l'embedding pour le livre {book_id}")
                else:
                    logging.warning("Modèle d'embedding non disponible")
            except Exception as e:
                logging.error(f"Erreur lors de la génération de l'embedding : {e}")

        # Lancement du traitement PDF en arrière-plan
        thread = Thread(target=encode_pdf, args=(
            current_app._get_current_object(),
            pdf_path,
            db_path,
            pdf_filename,
            int(form_data.get('begin', 0)),
            int(form_data.get('end', 0)),
            illustration_value
        ))
        thread.start()

        # Création de la réponse
        response = BookResponseDTO(
            id=book_id,
            title=book_creation_request.title,
            author=book_creation_request.author,
            description=book_creation_request.description,
            cover_image=book_creation_request.cover_image,
            filename=book_creation_request.filename,
            owner_id='system',
            public=book_creation_request.public
        )

        return jsonify(response.to_dict()), 201

    except Exception as e:
        logging.error(f"Error creating book: {e}")
        return jsonify({"error": str(e)}), 500


@book_bp.route('/', methods=['GET'])
def get_books_route():
    """
    Récupère la liste des livres accessibles à l'utilisateur.
    
    Args:
        current_user (dict): Informations sur l'utilisateur courant
        
    Returns:
        JSON: Liste des livres
        500: En cas d'erreur serveur
    """
    try:
        # Obtenir les paramètres de pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # Récupération des livres
        books_data = book_service.get_all_books()
        logging.info(f"Found {len(books_data)} books in database")
        
        # Calculer le nombre total de livres
        total = len(books_data)
        
        # Calculer l'index de début et de fin pour la pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # Sélectionner uniquement les livres de la page courante
        paginated_books = books_data[start_idx:end_idx]
        
        # Convertir les données en DTOs
        book_dtos = []
        for book in paginated_books:
            book_dto = BookResponseDTO(
                id=book.get('_id', ''),
                title=book.get('title', ''),
                author=book.get('author', ''),
                description=book.get('description'),
                cover_image=book.get('cover_image'),
                filename=book.get('pdf_path'),
                owner_id=book.get('proprietary'),  # Utiliser proprietary comme owner_id
                public=book.get('public', False),
                created_at=book.get('created_at'),
                updated_at=book.get('updated_at'),
                category=book.get('category'),
                subcategory=book.get('subcategory')
            )
            book_dtos.append(book_dto)
        
        # Créer le DTO de réponse
        response = BookListResponseDTO(
            books=book_dtos,
            total=total,
            page=page,
            per_page=per_page
        )
        
        return jsonify(response.to_dict()), 200
    except Exception as e:
        logging.error(f"Error getting books: {e}")
        return jsonify({"error": str(e)}), 500

@book_bp.route('/<book_id>', methods=['GET'])
def get_book_route(book_id):
    """
        Récupère les détails d'un livre spécifique par son ID.

        Args:
            current_user (dict): Informations sur l'utilisateur authentifié
            book_id (str): Identifiant unique du livre

        Returns:
            JSON: Détails du livre demandé
            
        Status Codes:
            200: Livre trouvé et retourné avec succès
            404: Livre non trouvé
            500: Erreur serveur lors de la récupération
    """
    try:
        logging.info(f"Getting book with ID: {book_id}")
        book = book_service.get_book_by_id(book_id)
        if not book:
            return jsonify({"error": "Book not found"}), 404
            
        
        # Création du DTO de réponse
        response = BookResponseDTO(
            id=book.get('_id', ''),
            title=book.get('title', ''),
            author=book.get('author', ''),
            description=book.get('description'),
            cover_image=book.get('cover_image'),
            filename=book.get('pdf_path'),
            owner_id=book.get('proprietary'),
            public=book.get('public', False),
            created_at=book.get('created_at'),
            updated_at=book.get('updated_at'),
            category=book.get('category'),
            subcategory=book.get('subcategory')
        )
        
        return jsonify(response.to_dict()), 200
    except Exception as e:
        logging.error(f"Error getting book: {e}")
        return jsonify({"error": str(e)}), 500

@book_bp.route('/<book_id>', methods=['PUT'])
def update_book_route(book_id):
    """
    Met à jour les informations d'un livre existant.
    Réservé aux administrateurs.

    Args:
        current_user (dict): Informations sur l'utilisateur authentifié
        book_id (str): Identifiant unique du livre à mettre à jour

    Form Data:
        cover_image (file, optional): Nouvelle image de couverture
        [autres champs]: Autres informations du livre à mettre à jour

    Returns:
        JSON: Message de confirmation ou d'erreur

    Status Codes:
        200: Livre mis à jour avec succès
        403: Accès non autorisé (utilisateur non admin)
        500: Erreur lors de la mise à jour
    """
    try:
        # Récupération des données de formulaire
        form_data = request.form.to_dict()
        
        # Création du DTO de mise à jour
        book_update_request = BookUpdateRequestDTO(
            title=form_data.get('title'),
            author=form_data.get('author'),
            description=form_data.get('description'),
            public=None if 'public' not in form_data else form_data.get('public').lower() == 'true'
        )
        
        # Gestion de l'image de couverture
        if 'cover_image' in request.files:
            cover_image = request.files['cover_image']
            filename = cover_image.filename
            cover_image_path = os.path.join(current_app.config['IMAGE_FOLDER'], filename)
            cover_image.save(cover_image_path)
            book_update_request.cover_image = filename
        
        # Conversion du DTO en dictionnaire pour la mise à jour
        update_data = book_update_request.to_dict()
        
        # Ajout de champs supplémentaires spécifiques à notre implémentation
        if 'edition' in form_data:
            update_data['edition'] = form_data['edition']
        if 'category' in form_data:
            update_data['category'] = form_data['category']
        if 'subcategory' in form_data:
            update_data['subcategory'] = form_data['subcategory']
        
        # Mise à jour du livre
        if book_service.update_book(book_id, update_data):
            # Génération de l'embedding si la description a été mise à jour
            if book_update_request.description and book_update_request.description.strip():
                try:
                    from ..utils.book_embedding_utils import generate_description_embedding
                    if hasattr(current_app, 'model'):
                        embedding_data, model_name, timestamp = generate_description_embedding(
                            book_update_request.description, current_app.model
                        )
                        if embedding_data:
                            book_service.update_book(book_id, {
                                'description_embedding': embedding_data,
                                'description_embedding_model': model_name,
                                'description_embedding_date': timestamp
                            })
                            logging.info(f"Embedding mis à jour pour le livre {book_id}")
                        else:
                            logging.warning(f"Échec de la mise à jour de l'embedding pour le livre {book_id}")
                    else:
                        logging.warning("Modèle d'embedding non disponible")
                except Exception as e:
                    logging.error(f"Erreur lors de la mise à jour de l'embedding : {e}")
            
            # Récupération du livre mis à jour
            updated_book = book_service.get_book_by_id(book_id)
            
            # Création du DTO de réponse
            response = BookResponseDTO(
                id=updated_book.get('_id', ''),
                title=updated_book.get('title', ''),
                author=updated_book.get('author', ''),
                description=updated_book.get('description'),
                cover_image=updated_book.get('cover_image'),
                filename=updated_book.get('pdf_path'),
                owner_id=updated_book.get('proprietary'),
                public=updated_book.get('public', False),
                created_at=updated_book.get('createdAt'),
                updated_at=updated_book.get('updatedAt'),
                category=updated_book.get('category'),
                subcategory=updated_book.get('subcategory')
            )
            
            return jsonify(response.to_dict()), 200
        return jsonify({"error": "Failed to update book"}), 500
    except Exception as e:
        logging.error(f"Error updating book: {e}")
        return jsonify({"error": str(e)}), 500

@book_bp.route('/<book_id>', methods=['DELETE'])
def delete_book_route(book_id):
    """
    Supprime un livre de la base de données.
    Réservé aux administrateurs.

    Args:
        current_user (dict): Informations sur l'utilisateur authentifié
        book_id (str): Identifiant unique du livre à supprimer

    Returns:
        JSON: Message de confirmation ou d'erreur

    Status Codes:
        200: Livre supprimé avec succès
        403: Accès non autorisé (utilisateur non admin)
        500: Erreur lors de la suppression
    """
    try:
        if book_service.delete_book(book_id):
            return jsonify({"message": "Book deleted"}), 200
        return jsonify({"error": "Failed to delete book"}), 500
    except Exception as e:
        logging.error(f"Error deleting book: {e}")
        return jsonify({"error": str(e)}), 500
    
    
@book_bp.route('/generate-cover', methods=['POST'])
def generate_book_cover():
    """
    Génère une image de couverture pour un livre à partir de la première page du PDF.
    
    Expected JSON body:
        filename (str): Nom du fichier PDF du livre
    
    Returns:
        JSON: Message de confirmation et nom du fichier image généré
        400: Si le filename est manquant ou le livre n'est pas trouvé
        500: En cas d'erreur lors de la génération
    """
    try:
        # Conversion de la requête JSON en DTO
        cover_request = GenerateCoverRequestDTO.from_dict(request.json)
        
        # Validation des données
        if not cover_request.filename:
            return jsonify({"error": "filename is required"}), 400
            
        # Récupérer le livre
        book = book_service.get_book_by_filename(cover_request.filename)
        if not book:
            return jsonify({"error": "Book not found"}), 404
            
        # Construire le chemin complet du PDF
        pdf_path = os.path.join(current_app.config['PDF_FOLDER'], book['pdf_path'])
        if not os.path.exists(pdf_path):
            return jsonify({"error": "PDF file not found"}), 404
            
        # Générer l'image de couverture
        image_filename, img = convert_pdf_page_to_image(
            pdf_path=pdf_path,
            page_number=0,
            max_width=400,
            output_format='webp'
        )
        
        if not image_filename or not img:
            return jsonify({"error": "Failed to generate cover image"}), 500
            
        # Sauvegarder l'image
        image_path = os.path.join(current_app.config['IMAGE_FOLDER'], image_filename)
        img.save(image_path, format='WEBP', quality=85)
        
        # Mettre à jour le livre dans la base de données
        update_result = book_service.update_book(
            book['_id'],
            {'cover_image': image_filename}
        )
        
        if not update_result:
            # Supprimer l'image si la mise à jour a échoué
            os.remove(image_path)
            return jsonify({"error": "Failed to update book record"}), 500
        
        # Récupération du livre mis à jour
        updated_book = book_service.get_book_by_id(book['_id'])
        
        # Création du DTO de réponse
        response = BookResponseDTO(
            id=updated_book.get('_id', ''),
            title=updated_book.get('title', ''),
            author=updated_book.get('author', ''),
            description=updated_book.get('description'),
            cover_image=image_filename,
            filename=updated_book.get('pdf_path'),
            owner_id=updated_book.get('proprietary'),
            public=updated_book.get('public', False),
            created_at=updated_book.get('created_at'),
            updated_at=updated_book.get('updated_at'),
            category=updated_book.get('category'),
            subcategory=updated_book.get('subcategory')
        )
        
        return jsonify({
            "message": "Cover image generated successfully",
            "cover_image": image_filename,
            "book": response.to_dict()
        }), 200
        
    except Exception as e:
        logging.error(f"Error generating cover image: {e}")
        return jsonify({"error": str(e)}), 500

@book_bp.route('/generate_description', methods=['POST'])
def generate_description_route():
    """
    Génère une description automatique pour un livre à partir de son contenu.
    Réservé aux administrateurs.

    Args:
        current_user (dict): Informations sur l'utilisateur authentifié

    JSON Body:
        pdf_files (list): Liste des chemins vers les fichiers PDF
        context (str): Contexte pour la génération de la description

    Returns:
        JSON: Description générée

    Status Codes:
        200: Description générée avec succès
        400: Paramètres requis manquants
        403: Accès non autorisé (utilisateur non admin)
        500: Erreur lors de la génération
    """
    try:
        # Conversion de la requête JSON en DTO
        description_request = DescriptionGenerationRequestDTO.from_dict(request.json)
        
        # Validation des données
        if not description_request.pdf_files:
            return jsonify({"error": "PDF files are required"}), 400

        # Pour cet exemple, nous ne considérons que le premier fichier PDF
        pdf_file = description_request.pdf_files[0] if description_request.pdf_files else None
        
        files_book = load_processed_data(current_app, pdf_file)
        if not files_book:
            return jsonify({"error": "Unable to load book data"}), 500

        description = reduceTextForDescriptions(
            files_book.description,
            description_request.context or "",
            length=250
        )
        
        # Récupération du livre associé
        book = book_service.get_book_by_filename(pdf_file)
        
        if book:
            # Mise à jour de la description dans la base de données
            book_service.update_book(book['_id'], {'description': description})
            
            # Récupération du livre mis à jour
            updated_book = book_service.get_book_by_id(book['_id'])
            
            # Création du DTO de réponse
            response = BookResponseDTO(
                id=updated_book.get('_id', ''),
                title=updated_book.get('title', ''),
                author=updated_book.get('author', ''),
                description=description,
                cover_image=updated_book.get('cover_image'),
                filename=updated_book.get('pdf_path'),
                owner_id=updated_book.get('proprietary'),
                public=updated_book.get('public', False),
                created_at=updated_book.get('created_at'),
                updated_at=updated_book.get('updated_at'),
                category=updated_book.get('category'),
                subcategory=updated_book.get('subcategory')
            )
            
            return jsonify({
                "description": description,
                "book": response.to_dict()
            }), 200
        
        # Si le livre n'est pas trouvé, retourner simplement la description
        return jsonify({"description": description}), 200

    except Exception as e:
        logging.error(f"Error generating description: {e}")
        return jsonify({"error": str(e)}), 500


@book_bp.route('/title/<title>/descriptions', methods=['GET'])
def get_descriptions_by_title_route(title):
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

@book_bp.route('/title/<title>/similarity', methods=['POST'])
def get_similarity_by_title_route(title):
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


@book_bp.route('/search', methods=['POST'])
def search_books_route():
    """
    Recherche des livres par similarité sémantique de description.
    
    JSON Body:
        query (str): Requête de recherche
        k (int, optional): Nombre maximum de résultats (défaut: 5, max: 50)
        threshold (float, optional): Seuil de similarité minimum (défaut: 0.5)
        category (str, optional): Filtrer par catégorie
        author (str, optional): Filtrer par auteur
    
    Returns:
        JSON: Résultats de recherche avec scores de similarité
        
    Status Codes:
        200: Recherche effectuée avec succès
        400: Paramètres de requête invalides
        500: Erreur lors de la recherche
    """
    try:
        start_time = time.time()
        
        # Validation et création du DTO de requête
        if not request.json:
            return jsonify({"error": "JSON body required"}), 400
            
        search_request = BookSearchRequestDTO.from_dict(request.json)
        
        if not search_request.is_valid():
            return jsonify({"error": "Query parameter is required and cannot be empty"}), 400
        
        logging.info(f"Recherche de livres pour: '{search_request.query}' (k={search_request.k}, threshold={search_request.threshold})")
        
        # Effectuer la recherche
        search_results = book_service.search_books_by_description(
            search_request.query,
            top_k=search_request.k,
            threshold=search_request.threshold
        )
        
        # Appliquer des filtres supplémentaires si spécifiés
        if search_request.category or search_request.author:
            filtered_results = []
            for result in search_results:
                # Filtrer par catégorie
                if search_request.category and result.get('category', '').lower() != search_request.category.lower():
                    continue
                # Filtrer par auteur
                if search_request.author and search_request.author.lower() not in result.get('author', '').lower():
                    continue
                filtered_results.append(result)
            search_results = filtered_results
        
        # Convertir les résultats en DTOs
        result_dtos = [
            BookSearchResultDTO.from_book_data(result.copy()) 
            for result in search_results
        ]
        
        # Calculer le temps d'exécution
        execution_time = time.time() - start_time
        
        # Créer la réponse
        response = BookSearchResponseDTO(
            results=result_dtos,
            query=search_request.query,
            total_found=len(result_dtos),
            execution_time=execution_time
        )
        
        logging.info(f"Recherche terminée: {len(result_dtos)} résultats en {execution_time:.3f}s")
        
        return jsonify(response.to_dict()), 200
        
    except Exception as e:
        logging.error(f"Error in book search: {e}")
        return jsonify({"error": str(e)}), 500


@book_bp.route('/embeddings/stats', methods=['GET'])
def get_embedding_stats_route():
    """
    Récupère les statistiques des embeddings pour tous les livres.
    
    Returns:
        JSON: Statistiques des embeddings
        
    Status Codes:
        200: Statistiques récupérées avec succès
        500: Erreur lors de la récupération
    """
    try:
        stats = book_service.get_embedding_stats()
        
        if 'error' in stats:
            return jsonify(stats), 500
            
        stats_dto = EmbeddingStatsDTO.from_dict(stats)
        
        return jsonify(stats_dto.to_dict()), 200
        
    except Exception as e:
        logging.error(f"Error getting embedding stats: {e}")
        return jsonify({"error": str(e)}), 500


@book_bp.route('/embeddings/migrate', methods=['POST'])
def migrate_embeddings_route():
    """
    Lance la migration des embeddings pour tous les livres qui en ont besoin.
    
    JSON Body:
        batch_size (int, optional): Nombre de livres à traiter par lot (défaut: 10)
    
    Returns:
        JSON: Résumé de la migration
        
    Status Codes:
        200: Migration effectuée avec succès
        500: Erreur lors de la migration
    """
    try:
        batch_size = 10
        if request.json and 'batch_size' in request.json:
            batch_size = max(1, min(request.json['batch_size'], 100))  # Limiter entre 1 et 100
        
        logging.info(f"Début de la migration des embeddings (batch_size={batch_size})")
        
        result = book_service.migrate_embeddings(batch_size=batch_size)
        
        if 'error' in result:
            return jsonify(result), 500
            
        return jsonify(result), 200
        
    except Exception as e:
        logging.error(f"Error in embedding migration: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# ENDPOINTS SIMPLIFIÉS POUR UXMCP
# =============================================================================

@book_bp.route('/simple-search', methods=['POST'])
def simple_search_books():
    """
    Endpoint simplifié pour recherche de livres - optimisé pour UXMCP agents.
    
    JSON Body:
        query (str): Requête de recherche
        limit (int, optional): Nombre de résultats (défaut: 3)
    
    Returns:
        JSON: Liste simplifiée des livres trouvés
    """
    try:
        data = request.get_json()
        if not data or not data.get('query'):
            return jsonify({"error": "query parameter is required"}), 400
            
        query = data['query']
        limit = min(data.get('limit', 3), 10)  # Max 10 résultats
        
        # Recherche avec seuil bas pour plus de résultats
        search_results = book_service.search_books_by_description(
            query, top_k=limit, threshold=0.3
        )
        
        # Format simplifié pour les agents
        simplified_results = []
        for result in search_results:
            simplified_results.append({
                "title": result.get('title', ''),
                "author": result.get('author', ''),
                "description": result.get('description', '')[:200] + "..." if len(result.get('description', '')) > 200 else result.get('description', ''),
                "file_path": result.get('pdf_path', ''),
                "category": result.get('category', ''),
                "similarity_score": round(result.get('similarity_score', 0), 3)
            })
        
        return jsonify({
            "query": query,
            "found": len(simplified_results),
            "books": simplified_results
        }), 200
        
    except Exception as e:
        logging.error(f"Error in simple book search: {e}")
        return jsonify({"error": str(e)}), 500


@book_bp.route('/simple-query', methods=['POST'])
def simple_query_books():
    """
    Endpoint simplifié pour interroger des livres - optimisé pour UXMCP agents.
    
    JSON Body:
        question (str): Question à poser
        files (list): Liste des chemins de fichiers PDF
        max_pages (int, optional): Nombre max de pages (défaut: 20)
    
    Returns:
        JSON: Réponse directe sans streaming
    """
    try:
        data = request.get_json()
        if not data or not data.get('question') or not data.get('files'):
            return jsonify({"error": "question and files parameters are required"}), 400
            
        question = data['question']
        files = data['files']
        max_pages = min(data.get('max_pages', 20), 50)  # Max 50 pages
        
        if not isinstance(files, list) or len(files) == 0:
            return jsonify({"error": "files must be a non-empty list"}), 400
            
        # Vérifier que les fichiers existent
        for file_path in files:
            full_path = os.path.join(current_app.config['PDF_FOLDER'], file_path)
            if not os.path.exists(full_path):
                return jsonify({"error": f"File not found: {file_path}"}), 404
        
        # Utiliser le système RAG existant pour traiter la question
        from app.pdf_aiEncode import process_query_simple
        
        try:
            # Appeler le système de traitement existant
            # Préparer l'objet app au format attendu par process_query avec la bonne configuration
            app_context = {
                'config': {
                    'device': current_app.config.get('DEVICE', 'cpu'),
                    'API_KEY': current_app.config.get('GROQ_API_KEY'),  # Utiliser la clé Groq
                    'AI_MODEL_TYPE': current_app.config.get('AI_MODEL_TYPE', 'groq'),
                    'AI_MODEL_TYPE_FOR_RESPONSE': current_app.config.get('AI_MODEL_TYPE_FOR_RESPONSE', 'groq'),
                    'GROQ_MODEL_NAME': current_app.config.get('GROQ_MODEL_NAME', 'moonshotai/kimi-k2-instruct'),
                    'FOLDER_PATH': current_app.config.get('FOLDER_PATH', 'db'),
                    'PDF_FOLDER': current_app.config.get('PDF_FOLDER', 'pdf')
                },
                'model': current_app.model if hasattr(current_app, 'model') else None
            }
            
            rag_response = process_query_simple(
                app_context,
                question,
                files,
                max_pages
            )
            
            # Extraire la réponse et les sources
            answer = rag_response.get('answer', 'Pas de réponse générée')
            sources = []
            
            if 'matches' in rag_response and 'all_matches' in rag_response['matches']:
                for match in rag_response['matches']['all_matches'][:5]:  # Top 5 sources
                    sources.append({
                        "file": match.get('file', ''),
                        "page": match.get('page_num', 0),
                        "text_excerpt": match.get('text', '')[:150] + "..." if len(match.get('text', '')) > 150 else match.get('text', ''),
                        "relevance_score": round(match.get('score', 0), 3)
                    })
            
            response_data = {
                "question": question,
                "files_processed": files,
                "answer": answer,
                "sources": sources,
                "processing_info": {
                    "files_count": len(files),
                    "max_pages_per_file": max_pages,
                    "sources_found": len(sources)
                }
            }
            
        except Exception as rag_error:
            logging.error(f"RAG processing error: {rag_error}")
            # Fallback en cas d'erreur
            response_data = {
                "question": question,
                "files_processed": files,
                "answer": f"Erreur lors du traitement de la question avec le système RAG: {str(rag_error)}",
                "sources": [],
                "processing_info": {
                    "files_count": len(files),
                    "max_pages_per_file": max_pages,
                    "error": str(rag_error)
                }
            }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logging.error(f"Error in simple book query: {e}")
        return jsonify({"error": str(e)}), 500


@book_bp.route('/agent-search-and-ask', methods=['POST'])
def agent_search_and_ask():
    """
    Endpoint combiné pour rechercher des livres et poser une question - optimisé pour agents UXMCP.
    
    JSON Body:
        search_query (str): Requête pour rechercher des livres
        question (str): Question à poser aux livres trouvés
        max_books (int, optional): Nombre max de livres à interroger (défaut: 2)
        max_pages (int, optional): Nombre max de pages par livre (défaut: 15)
    
    Returns:
        JSON: Résultats de recherche + réponse à la question
    """
    try:
        data = request.get_json()
        if not data or not data.get('search_query') or not data.get('question'):
            return jsonify({"error": "search_query and question parameters are required"}), 400
            
        search_query = data['search_query']
        question = data['question']
        max_books = min(data.get('max_books', 2), 5)  # Max 5 livres
        max_pages = min(data.get('max_pages', 15), 30)  # Max 30 pages
        
        # Étape 1: Rechercher des livres pertinents
        search_results = book_service.search_books_by_description(
            search_query, top_k=max_books, threshold=0.4
        )
        
        if not search_results:
            return jsonify({
                "search_query": search_query,
                "question": question,
                "books_found": 0,
                "answer": "Aucun livre pertinent trouvé pour cette recherche.",
                "books": []
            }), 200
        
        # Étape 2: Préparer les fichiers pour l'interrogation
        selected_books = []
        file_paths = []
        
        for result in search_results:
            if result.get('pdf_path'):
                file_paths.append(result['pdf_path'])
                selected_books.append({
                    "title": result.get('title', ''),
                    "author": result.get('author', ''),
                    "file_path": result.get('pdf_path', ''),
                    "similarity_score": round(result.get('similarity_score', 0), 3)
                })
        
        # Étape 3: Interroger les livres trouvés
        if file_paths:
            try:
                # Utiliser le système RAG pour interroger les livres
                app_context = {
                    'config': {
                        'device': current_app.config.get('DEVICE', 'cpu'),
                        'API_KEY': current_app.config.get('GROQ_API_KEY'),
                        'AI_MODEL_TYPE': current_app.config.get('AI_MODEL_TYPE', 'groq'),
                        'AI_MODEL_TYPE_FOR_RESPONSE': current_app.config.get('AI_MODEL_TYPE_FOR_RESPONSE', 'groq'),
                        'GROQ_MODEL_NAME': current_app.config.get('GROQ_MODEL_NAME', 'moonshotai/kimi-k2-instruct'),
                        'FOLDER_PATH': current_app.config.get('FOLDER_PATH', 'db'),
                        'PDF_FOLDER': current_app.config.get('PDF_FOLDER', 'pdf')
                    },
                    'model': current_app.model if hasattr(current_app, 'model') else None
                }
                
                from app.pdf_aiEncode import process_query_simple
                rag_response = process_query_simple(app_context, question, file_paths, max_pages)
                answer = rag_response.get('answer', f"Réponse basée sur l'analyse de {len(selected_books)} livre(s) trouvé(s).")
                
            except Exception as e:
                logging.error(f"Erreur lors de l'interrogation RAG: {e}")
                answer = f"Erreur lors de l'analyse des livres: {str(e)}"
        else:
            answer = "Aucun livre trouvé pour répondre à cette question."
        
        return jsonify({
            "search_query": search_query,
            "question": question,
            "books_found": len(selected_books),
            "books": selected_books,
            "answer": answer,
            "processing_info": {
                "books_analyzed": len(selected_books),
                "max_pages_per_book": max_pages,
                "search_threshold": 0.4
            }
        }), 200
        
    except Exception as e:
        logging.error(f"Error in agent search and ask: {e}")
        return jsonify({"error": str(e)}), 500


@book_bp.route('/get-sources', methods=['POST'])
def get_sources_route():
    """
    Récupère les sources les plus pertinentes pour une requête.
    Peut sélectionner automatiquement les livres les plus pertinents si aucun fichier n'est spécifié.
    
    JSON Body:
        query (str): Question à analyser (requis)
        files (list, optional): Liste des chemins PDF. Si non fourni, sélection automatique
        k (int, optional): Nombre de sources à retourner (défaut: 5, max: 20)
        max_pages (int, optional): Nombre max de pages par livre (défaut: 30, max: 100)
        auto_select_books (int, optional): Nombre de livres à sélectionner automatiquement (défaut: 2, max: 5)
    
    Returns:
        JSON: Sources pertinentes avec métadonnées
    """
    try:
        data = request.get_json()
        if not data or not data.get('query'):
            return jsonify({"error": "query parameter is required"}), 400
            
        query = data['query']
        files = data.get('files')  # Peut être None pour sélection automatique
        k = min(max(data.get('k', 5), 1), 20)
        max_pages = min(max(data.get('max_pages', 30), 5), 100)
        auto_select_books = min(max(data.get('auto_select_books', 2), 1), 5)
        
        # Valider les fichiers si fournis
        if files is not None:
            if not isinstance(files, list):
                return jsonify({"error": "files must be a list or null for automatic selection"}), 400
            
            # Vérifier que les fichiers existent
            for file_path in files:
                full_path = os.path.join(current_app.config['PDF_FOLDER'], file_path)
                if not os.path.exists(full_path):
                    return jsonify({"error": f"File not found: {file_path}"}), 404
        
        # Préparer l'objet app au format attendu
        app_context = {
            'config': {
                'device': current_app.config.get('DEVICE', 'cpu'),
                'API_KEY': current_app.config.get('GROQ_API_KEY'),
                'AI_MODEL_TYPE': current_app.config.get('AI_MODEL_TYPE', 'groq'),
                'AI_MODEL_TYPE_FOR_RESPONSE': current_app.config.get('AI_MODEL_TYPE_FOR_RESPONSE', 'groq'),
                'GROQ_MODEL_NAME': current_app.config.get('GROQ_MODEL_NAME', 'moonshotai/kimi-k2-instruct'),
                'FOLDER_PATH': current_app.config.get('FOLDER_PATH', 'db'),
                'PDF_FOLDER': current_app.config.get('PDF_FOLDER', 'pdf')
            },
            'model': current_app.model if hasattr(current_app, 'model') else None
        }
        
        # Appeler la fonction de récupération des sources
        from app.pdf_aiEncode import get_relevant_sources_simple
        
        result = get_relevant_sources_simple(
            app_context,
            query,
            files=files,
            k=k,
            max_pages=max_pages,
            auto_select_books=auto_select_books
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logging.error(f"Error in get sources: {e}")
        return jsonify({"error": str(e)}), 500