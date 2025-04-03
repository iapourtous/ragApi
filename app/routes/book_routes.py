import logging
import os
from threading import Thread
from flask import Blueprint, jsonify, request, current_app
from app.pdf_aiEncode import encode_pdf
from app.services import BookService
from app.utils.ai_utils import reduceTextForDescriptions
from app.utils.auth_utils import token_required
from app.utils.file_utils import load_processed_data, save_processed_data
from app.utils.images_utils import convert_pdf_page_to_image
from app.utils.vector_utils import compare_query_to_descriptions, serialize_tensor
from app.dto.book_dto import (
    BookCreationRequestDTO, BookUpdateRequestDTO, BookResponseDTO, 
    BookListResponseDTO, GenerateCoverRequestDTO, DescriptionGenerationRequestDTO
)

book_bp = Blueprint('book', __name__)
book_service = BookService()

@book_bp.route('/', methods=['POST'])
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
        form_data = request.form.to_dict()
        
        # Création du DTO pour la requête
        book_creation_request = BookCreationRequestDTO(
            title=form_data.get('title', ''),
            author=form_data.get('author', ''),
            description=form_data.get('description'),
            public=form_data.get('public', 'false').lower() == 'true'
        )
        
        # Ajout de propriétés supplémentaires spécifiques à notre implémentation
        form_data['proprietary'] = current_user['username']

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
        book_id = book_service.create_book({
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
        })

        if not book_id:
            return jsonify({"error": "Failed to create book"}), 500

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
            owner_id=current_user.get('id', ''),
            public=book_creation_request.public
        )

        return jsonify(response.to_dict()), 201

    except Exception as e:
        logging.error(f"Error creating book: {e}")
        return jsonify({"error": str(e)}), 500


@book_bp.route('/', methods=['GET'])
@token_required
def get_books_route(current_user):
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
        books_data = book_service.get_all_books(current_user)
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
                updated_at=book.get('updated_at')
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
@token_required
def get_book_route(current_user, book_id):
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
            
        # Vérification des droits d'accès
        if not book.get('public') and book.get('proprietary') != current_user.get('username') and current_user['role'] != 'admin':
            return jsonify({"error": "You don't have access to this book"}), 403
        
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
            updated_at=book.get('updated_at')
        )
        
        return jsonify(response.to_dict()), 200
    except Exception as e:
        logging.error(f"Error getting book: {e}")
        return jsonify({"error": str(e)}), 500

@book_bp.route('/<book_id>', methods=['PUT'])
@token_required
def update_book_route(current_user, book_id):
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
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Admin privileges required'}), 403
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
                updated_at=updated_book.get('updatedAt')
            )
            
            return jsonify(response.to_dict()), 200
        return jsonify({"error": "Failed to update book"}), 500
    except Exception as e:
        logging.error(f"Error updating book: {e}")
        return jsonify({"error": str(e)}), 500

@book_bp.route('/<book_id>', methods=['DELETE'])
@token_required
def delete_book_route(current_user, book_id):
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
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Admin privileges required'}), 403
    try:
        if book_service.delete_book(book_id):
            return jsonify({"message": "Book deleted"}), 200
        return jsonify({"error": "Failed to delete book"}), 500
    except Exception as e:
        logging.error(f"Error deleting book: {e}")
        return jsonify({"error": str(e)}), 500
    
    
@book_bp.route('/generate-cover', methods=['POST'])
@token_required
def generate_book_cover(current_user):
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
            updated_at=updated_book.get('updated_at')
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
@token_required
def generate_description_route(current_user):
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
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Admin privileges required'}), 403
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
                updated_at=updated_book.get('updated_at')
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
@token_required
def get_descriptions_by_title_route(current_user, title):
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
@token_required
def get_similarity_by_title_route(current_user, title):
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