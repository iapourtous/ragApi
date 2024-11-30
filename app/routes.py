"""
Configuration et gestion des routes de l'application Flask.

Ce module définit toutes les routes de l'API REST, gérant l'authentification,
la manipulation des livres, le traitement des requêtes PDF et les interactions utilisateurs.

Routes principales :
    - Authentification (/login, /register)
    - Gestion des utilisateurs (/users)
    - Gestion des livres (/books)
    - Traitement PDF (/pdfai)
    - Gestion des messages de contact (/contact-messages)

Fonctionnalités :
    - Authentification JWT avec vérification reCAPTCHA
    - CRUD complet pour les livres et utilisateurs
    - Traitement et analyse de documents PDF
    - Gestion des similarités et descriptions de livres
    - Système de vote pour les réponses générées
    - Gestion des messages de contact

Sécurité :
    - Décorateur token_required pour la protection des routes
    - Vérification reCAPTCHA pour les actions sensibles
    - Contrôle des rôles utilisateurs (admin/user)
    - Validation des entrées utilisateur

Dépendances principales :
    - Flask : Framework web
    - JWT : Gestion des tokens d'authentification
    - reCAPTCHA : Protection contre les bots
    - Services : BookService, UserService, QueryDataService, ContactMessageService

Usage:
    Le module est importé et utilisé par l'application principale Flask.
    Les routes sont configurées via la fonction setup_routes(app).

Example:
    from app import create_app
    app = create_app()
    
    # Les routes sont maintenant accessibles :
    # POST /login
    # POST /register
    # GET /books
    # etc.

Notes:
    - Toutes les réponses sont au format JSON
    - Les erreurs sont gérées de manière cohérente avec des codes HTTP appropriés
    - Les opérations sensibles nécessitent des droits d'administration
    - Les fichiers sont servis de manière sécurisée avec vérification des chemins
"""

from threading import Thread
from flask import jsonify, request, current_app, send_from_directory, abort
from flask_cors import CORS
from functools import wraps
import jwt
import logging
import os
import requests
from datetime import datetime, timedelta

from app.utils.images_utils import convert_pdf_page_to_image
from app.utils.vector_utils import compare_query_to_descriptions, serialize_tensor
from app.utils.file_utils import load_processed_data, save_processed_data
from app.utils.ai_utils import reduceTextForDescriptions
from app.pdf_processing import process_query
from app.background_tasks import process_pdf
from app.services.contactMessageService import ContactMessageService

# Import des services
from app.services import BookService, UserService, QueryDataService, ServiceManager

# Initialisation des services
services = ServiceManager()
user_service = UserService()
book_service = BookService()
query_service = QueryDataService()
contact_message_service = ContactMessageService()

def token_required(f):
    """
    Décorateur pour protéger les routes nécessitant une authentification par token JWT.
    
    Vérifie la présence et la validité du token JWT dans l'en-tête Authorization.
    Si le token est valide, ajoute les informations de l'utilisateur à la requête.
    
    Args:
        f: La fonction à décorer
        
    Returns:
        Function: La fonction décorée
        
    Raises:
        401: Si le token est manquant ou invalide
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = {
                'username': data['username'],
                'role': data['role']
            }
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def verify_recaptcha(token,action):
    """
    Valide un token reCAPTCHA avec l'API reCAPTCHA Enterprise.
    
    Args:
        token (str): Le token reCAPTCHA fourni par le client
        action (str): L'action attendue (ex: 'LOGIN', 'REGISTER')
        
    Returns:
        tuple: (success: bool, score: float)
            - success: True si la validation est réussie
            - score: Score de risque entre 0 et 1
    """
    # Replace with your project ID
    PROJECT_ID = 'formal-outpost-271911'

    # Get the API key and site key from your Flask app configuration
    API_KEY = current_app.config['RECAPTCHA_API_KEY']      # Add this to your config
    SITE_KEY = current_app.config['RECAPTCHA_SITE_KEY']    # Add this to your config

    # Build the URL
    url = f'https://recaptchaenterprise.googleapis.com/v1/projects/{PROJECT_ID}/assessments?key={API_KEY}'

    # Create the request payload
    payload = {
        "event": {
            "token": token,
            "siteKey": SITE_KEY,
            "expectedAction": action,
        }
    }

    # Set the headers
    headers = {
        'Content-Type': 'application/json',
    }

    # Send the POST request to reCAPTCHA Enterprise API
    response = requests.post(url, json=payload, headers=headers)
    result = response.json()

    # Log the response for debugging
    logging.info(f"reCAPTCHA Enterprise response: {result}")

    # Check if the token is valid
    if 'tokenProperties' in result:
        token_properties = result['tokenProperties']
        if token_properties.get('valid'):
            # Token is valid
            # Get the risk analysis score
            risk_analysis = result.get('riskAnalysis', {})
            score = risk_analysis.get('score', 0.0)
            return True, score
        else:
            # Token is invalid, log the reason
            invalid_reason = token_properties.get('invalidReason')
            logging.warning(f"Invalid reCAPTCHA token: {invalid_reason}")
            return False, 0.0
    else:
        # Error in the response
        error = result.get('error', {})
        logging.error(f"Error in reCAPTCHA validation: {error}")
        return False, 0.0


def setup_routes(app):
    CORS(app)

    @app.route('/login', methods=['POST'])
    def login():
        """
        Gère l'authentification des utilisateurs.
        
        Vérifie les identifiants fournis et le token reCAPTCHA.
        Génère un token JWT en cas de succès.
        
        Returns:
            JSON: Token JWT et rôle de l'utilisateur en cas de succès
            401: Si les identifiants sont invalides
            400: Si le token reCAPTCHA est manquant
            403: Si la validation reCAPTCHA échoue
        """        
        auth = request.json
        
            # Vérification reCAPTCHA
        recaptcha_token = auth.get("captchaToken")
        if not recaptcha_token:
            return jsonify({"message": "reCAPTCHA token is missing"}), 400
        
        success, score = verify_recaptcha(recaptcha_token,"login")
        logging.info(f"Srore:{score}")
        if not success or score < 0.5:
            return jsonify({"message": "Failed reCAPTCHA validation"}), 403
            
        
        if not auth or not auth.get('username') or not auth.get('password'):
            return jsonify({'message': 'Could not verify'}), 401

        user = user_service.get_user_by_username(auth.get('username'))
        if not user:
            return jsonify({'message': 'User not found'}), 401

        if user.check_password(auth.get('password')):
            token = jwt.encode({
                'username': user.username,
                'role': user.role,
                'exp': datetime.utcnow() + timedelta(minutes=30)
            }, current_app.config['SECRET_KEY'], algorithm="HS256")

            return jsonify({
                'token': token.decode('UTF-8') if isinstance(token, bytes) else token,
                'role': user.role
            })

        return jsonify({'message': 'Invalid credentials'}), 401

    @app.route('/users', methods=['POST'])
    @token_required
    def create_user_route(current_user):
        """
        Crée un nouvel utilisateur (réservé aux administrateurs).
        
        Args:
            current_user (dict): Informations sur l'utilisateur courant
            
        Returns:
            JSON: Message de succès ou d'erreur
            201: Si l'utilisateur est créé avec succès
            400: Si les données sont invalides
            403: Si l'utilisateur n'est pas administrateur
        """
        if current_user['role'] != 'admin':
            return jsonify({'message': 'Admin privileges required'}), 403

        data = request.json
        success, message = user_service.create_user(
            username=data.get('username'),
            password=data.get('password'),
            role="user",
            email=data.get('email'),
            metadata=data.get('metadata', {})
        )

        if success:
            return jsonify({'message': message}), 201
        return jsonify({'message': message}), 400

    @app.route('/users/<username>', methods=['PUT'])
    @token_required
    def update_user_route(current_user, username):
        """
        Met à jour les informations d'un utilisateur.
        
        Args:
            current_user (dict): Informations sur l'utilisateur courant
            username (str): Nom d'utilisateur à mettre à jour
            
        Returns:
            JSON: Message de succès ou d'erreur
            404: Si l'utilisateur n'est pas trouvé
        """
        data = request.json
        if user_service.update(username, data):
            return jsonify({'message': 'User updated successfully'})
        return jsonify({'message': 'User not found'}), 404

    @app.route('/users/<username>', methods=['DELETE'])
    @token_required
    def delete_user_route(current_user, username):
        """
        Supprime un utilisateur (réservé aux administrateurs).
        
        Args:
            current_user (dict): Informations sur l'utilisateur courant
            username (str): Nom d'utilisateur à supprimer
            
        Returns:
            JSON: Message de succès ou d'erreur
            403: Si l'utilisateur n'est pas administrateur
            404: Si l'utilisateur à supprimer n'est pas trouvé
        """
        if current_user['role'] != 'admin':
            return jsonify({'message': 'Admin privileges required'}), 403

        if user_service.delete(username):
            return jsonify({'message': 'User deleted successfully'})
        return jsonify({'message': 'User not found'}), 404

    @app.route('/images/<filename>')
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

    @app.route('/pdf/<path:subpath>/<filename>')
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
        full_path = os.path.join(current_app.config['PDF_FOLDER'], subpath, filename)
        if os.path.exists(full_path) and os.path.commonpath([full_path, current_app.config['PDF_FOLDER']]) == current_app.config['PDF_FOLDER']:
            return send_from_directory(current_app.config['PDF_FOLDER'], os.path.join(subpath, filename))
        abort(404)

    @app.route('/books/title/<title>/descriptions', methods=['GET'])
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

    @app.route('/books/title/<title>/similarity', methods=['POST'])
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

    @app.route("/pdfai", methods=["POST"])
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

    @app.route('/books', methods=['POST'])
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
            thread = Thread(target=process_pdf, args=(
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

    @app.route('/books', methods=['GET'])
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
            books = book_service.get_all_books(current_user)
            return jsonify({"books": books}), 200
        except Exception as e:
            logging.error(f"Error getting books: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/books/<book_id>', methods=['GET'])
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
            book = book_service.get_by_id(book_id)
            if book:
                return jsonify(book), 200
            return jsonify({"error": "Book not found"}), 404
        except Exception as e:
            logging.error(f"Error getting book: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/books/<book_id>', methods=['PUT'])
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
            data = request.form.to_dict()
            if 'cover_image' in request.files:
                cover_image = request.files['cover_image']
                filename = cover_image.filename
                cover_image_path = os.path.join(current_app.config['IMAGE_FOLDER'], filename)
                cover_image.save(cover_image_path)
                data['cover_image'] = filename

            if book_service.update_book(book_id, data):
                return jsonify({"message": "Book updated"}), 200
            return jsonify({"error": "Failed to update book"}), 500
        except Exception as e:
            logging.error(f"Error updating book: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/books/<book_id>', methods=['DELETE'])
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
        
        
    @app.route('/books/generate-cover', methods=['POST'])
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
            # Vérifier les données d'entrée
            data = request.json
            if not data or 'filename' not in data:
                return jsonify({"error": "filename is required"}), 400
                
            filename = data['filename']
            
            # Récupérer le livre
            book = book_service.get_book_by_filename(filename)
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
                
            return jsonify({
                "message": "Cover image generated successfully",
                "cover_image": image_filename
            }), 200
            
        except Exception as e:
            logging.error(f"Error generating cover image: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/generate_description', methods=['POST'])
    @token_required
    def generate_description_route(current_user):
        """
        Génère une description automatique pour un livre à partir de son contenu.
        Réservé aux administrateurs.

        Args:
            current_user (dict): Informations sur l'utilisateur authentifié

        JSON Body:
            pdf_files (str): Chemin vers les fichiers PDF
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
            data = request.json
            if 'pdf_files' not in data or 'context' not in data:
                return jsonify({"error": "Missing required fields"}), 400

            files_book = load_processed_data(current_app, data.get("pdf_files"))
            if not files_book:
                return jsonify({"error": "Unable to load book data"}), 500

            description = reduceTextForDescriptions(
                files_book.description,
                data.get("context"),
                length=250
            )
            return jsonify({"description": description}), 200

        except Exception as e:
            logging.error(f"Error generating description: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/protected', methods=['GET'])
    @token_required
    def protected(current_user):
        """
        Route protégée pour tester l'authentification et renouveler le token.

        Args:
            current_user (dict): Informations sur l'utilisateur authentifié

        Returns:
            JSON: Message de confirmation et nouveau token JWT
        """
        token = jwt.encode({
            'username': current_user['username'],
            'role': current_user['role'],
            'exp': datetime.utcnow() + timedelta(minutes=30)
        }, current_app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({'message': 'This is a protected route!', 'token': token})

    @app.route('/books/filename/<path:filename>', methods=['GET'])
    @token_required
    def get_book_by_filename_route(current_user, filename):
        try:
            book = book_service.get_by_filename(filename)
            if book:
                return jsonify(book), 200
            return jsonify({"error": "Book not found"}), 404
        except Exception as e:
            logging.error(f"Error getting book by filename: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/vote", methods=["POST"])
    @token_required
    def vote(current_user):
        try:
            data = request.json
            query_id = data.get('queryId')
            vote_type = data.get('voteType')

            if not query_id or not vote_type:
                return jsonify({"error": "Missing queryId or voteType"}), 400

            if query_service.process_vote(query_id, vote_type):
                return jsonify({"message": "Vote recorded successfully"}), 200
            return jsonify({"error": "Failed to record vote"}), 500

        except Exception as e:
            logging.error(f"Error processing vote: {e}")
            return jsonify({"error": str(e)}), 500
        
    @app.route('/register', methods=['POST'])
    def register():
        """
        Gère l'inscription des nouveaux utilisateurs.
        
        Vérifie le token reCAPTCHA et crée un nouvel utilisateur.
        
        Returns:
            JSON: Token JWT et message de confirmation
            400: Si les données sont invalides ou l'utilisateur existe déjà
            403: Si la validation reCAPTCHA échoue
            500: En cas d'erreur serveur
        """
        try: 
            data = request.json
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            recaptcha_token = data.get('captchaToken')
            
            if not recaptcha_token:
                return jsonify({"message": "reCAPTCHA token is missing"}), 400

            # Validation reCAPTCHA
            success, score = verify_recaptcha(recaptcha_token,"signup")
            if not success or score < 0.8:
                return jsonify({"message": "Failed reCAPTCHA validation"}), 403           

            # Vérifier si l'utilisateur existe déjà
            if user_service.get_user_by_username(username):
                return jsonify({'message': 'Username already exists'}), 400
                
            if user_service.get_user_by_email(email):
                return jsonify({'message': 'Email already exists'}), 400

            # Créer le nouvel utilisateur
            success, message = user_service.create_user(
                username=username,
                password=password,
                email=email,
                role='user'  # Par défaut, les nouveaux utilisateurs ont le rôle 'user'
            )

            if success:
                # Générer un token pour le nouvel utilisateur
                token = jwt.encode({
                    'username': username,
                    'role': 'user',
                    'exp': datetime.utcnow() + timedelta(minutes=30)
                }, current_app.config['SECRET_KEY'], algorithm="HS256")

                return jsonify({
                    'message': 'User created successfully',
                    'token': token
                }), 201
            else:
                return jsonify({'message': message}), 400

        except Exception as e:
            logging.error(f"Error during registration: {e}")
            return jsonify({'message': 'An error occurred during registration'}), 500

    @app.route('/contact-messages', methods=['POST'])
    def create_contact_message():
        """
        Crée un nouveau message de contact.

        Vérifie le token reCAPTCHA pour s'assurer que la requête est légitime.
        Enregistre ensuite le message dans la base de données.

        Returns:
            JSON: Confirmation et ID du message créé en cas de succès
            400: Si les données ou le token reCAPTCHA sont manquants
            403: Si la validation reCAPTCHA échoue
            500: En cas d'erreur serveur
        """
        try:
            data = request.json
            if not data or not all(key in data for key in ['username', 'email', 'message']):
                return jsonify({'message': 'Données manquantes'}), 400

            # Vérification reCAPTCHA
            recaptcha_token = data.get("captchaToken")
            if not recaptcha_token:
                return jsonify({"message": "reCAPTCHA token is missing"}), 400

            success, score = verify_recaptcha(recaptcha_token, "contact")
            if not success or score < 0.5:
                return jsonify({"message": "Failed reCAPTCHA validation"}), 403

            message_id = contact_message_service.create_message({
                'username': data['username'],
                'email': data['email'],
                'message': data['message']
            })

            if message_id:
                return jsonify({
                    'message': 'Message créé avec succès',
                    'message_id': message_id
                }), 201
            return jsonify({'message': 'Erreur lors de la création du message'}), 500

        except Exception as e:
            logging.error(f"Erreur lors de la création du message de contact : {e}")
            return jsonify({'message': 'Erreur serveur'}), 500

    @app.route('/contact-messages', methods=['GET'])
    @token_required
    def get_all_contact_messages(current_user):
        """
        Récupère tous les messages de contact (réservé aux administrateurs).

        Args:
            current_user (dict): Informations sur l'utilisateur courant

        Returns:
            JSON: Liste des messages de contact
            403: Si l'utilisateur n'a pas les privilèges nécessaires
            500: En cas d'erreur serveur
        """
        try:
            if current_user['role'] != 'admin':
                return jsonify({'message': 'Accès non autorisé'}), 403

            messages = contact_message_service.get_all_messages()
            return jsonify({'messages': messages}), 200

        except Exception as e:
            logging.error(f"Erreur lors de la récupération des messages : {e}")
            return jsonify({'message': 'Erreur serveur'}), 500

    @app.route('/contact-messages/status/<status>', methods=['GET'])
    @token_required
    def get_contact_messages_by_status(current_user, status):
        """
        Récupère les messages de contact filtrés par statut (réservé aux administrateurs).

        Args:
            current_user (dict): Informations sur l'utilisateur courant
            status (str): Statut des messages à filtrer

        Returns:
            JSON: Liste des messages avec le statut spécifié
            403: Si l'utilisateur n'a pas les privilèges nécessaires
            500: En cas d'erreur serveur
        """
        try:
            if current_user['role'] != 'admin':
                return jsonify({'message': 'Accès non autorisé'}), 403

            messages = contact_message_service.get_messages_by_status(status)
            return jsonify({'messages': messages}), 200

        except Exception as e:
            logging.error(f"Erreur lors de la récupération des messages par statut : {e}")
            return jsonify({'message': 'Erreur serveur'}), 500

    @app.route('/contact-messages/<message_id>', methods=['DELETE'])
    @token_required
    def delete_contact_message(current_user, message_id):
        """
        Supprime un message de contact (réservé aux administrateurs).

        Args:
            current_user (dict): Informations sur l'utilisateur courant
            message_id (str): ID du message à supprimer

        Returns:
            JSON: Confirmation de la suppression
            403: Si l'utilisateur n'a pas les privilèges nécessaires
            404: Si le message n'est pas trouvé
            500: En cas d'erreur serveur
        """
        try:
            if current_user['role'] != 'admin':
                return jsonify({'message': 'Accès non autorisé'}), 403

            if contact_message_service.delete_message(message_id):
                return jsonify({'message': 'Message supprimé avec succès'}), 200
            return jsonify({'message': 'Message non trouvé'}), 404

        except Exception as e:
            logging.error(f"Erreur lors de la suppression du message : {e}")
            return jsonify({'message': 'Erreur serveur'}), 500

    return app