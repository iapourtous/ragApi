import logging
from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename
import os
from app.services import BlogService
from app.utils.auth_utils import token_required

blog_bp = Blueprint('blog', __name__)
blog_service = BlogService()

@blog_bp.route('/', methods=['POST'])
@token_required
def create_blog_route(current_user):
        """Crée un nouvel article de blog."""
        if current_user['role'] != 'admin':
            return jsonify({'message': 'Admin privileges required'}), 403
        
        try:
            data = request.form.to_dict()
            
            # Gestion de l'image d'illustration
            if 'image' in request.files:
                image = request.files['image']
                filename = image.filename
                image_path = os.path.join(current_app.config['IMAGE_FOLDER'], 'blog', filename)
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                image.save(image_path)
                data['image_url'] = f'/images/blog/{filename}'

            blog_id = blog_service.create_blog(data)
            if blog_id:
                return jsonify({
                    'message': 'Blog post created successfully',
                    'blog_id': blog_id
                }), 201
            return jsonify({'message': 'Failed to create blog post'}), 500
        except Exception as e:
            logging.error(f"Error creating blog post: {e}")
            return jsonify({'message': str(e)}), 500

@blog_bp.route('/', methods=['GET'])
def get_blogs_route():
    """Récupère tous les articles de blog."""
    try:
        visible_only = request.args.get('visible_only', 'true').lower() == 'true'
        category = request.args.get('category')
        
        if category:
            blogs = blog_service.get_blogs_by_category(category, visible_only)
        else:
            blogs = blog_service.get_all_blogs(visible_only)
            
        return jsonify({'blogs': blogs}), 200
    except Exception as e:
        logging.error(f"Error getting blog posts: {e}")
        return jsonify({'message': str(e)}), 500

@blog_bp.route('/<blog_id>', methods=['GET'])
def get_blog_route(blog_id):
    """Récupère un article de blog spécifique."""
    try:
        blog = blog_service.get_blog(blog_id)
        if blog:
            return jsonify(blog), 200
        return jsonify({'message': 'Blog post not found'}), 404
    except Exception as e:
        logging.error(f"Error getting blog post: {e}")
        return jsonify({'message': str(e)}), 500

@blog_bp.route('/url/<pretty_url>', methods=['GET'])
def get_blog_by_url_route(pretty_url):
    """Récupère un article de blog par son URL conviviale."""
    try:
        blog = blog_service.get_blog_by_pretty_url(pretty_url)
        if blog:
            return jsonify(blog), 200
        return jsonify({'message': 'Blog post not found'}), 404
    except Exception as e:
        logging.error(f"Error getting blog post: {e}")
        return jsonify({'message': str(e)}), 500

@blog_bp.route('/<blog_id>', methods=['PUT'])
@token_required
def update_blog_route(current_user, blog_id):
    """Met à jour un article de blog."""
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Admin privileges required'}), 403
        
    try:
        data = request.form.to_dict()
        
        if 'image' in request.files:
            image = request.files['image']
            filename = secure_filename(image.filename)
            image_path = os.path.join(current_app.config['IMAGE_FOLDER'], 'blog', filename)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image.save(image_path)
            data['image_url'] = f'/images/blog/{filename}'

        if blog_service.update_blog(blog_id, data):
            return jsonify({'message': 'Blog post updated successfully'})
        return jsonify({'message': 'Blog post not found'}), 404
    except Exception as e:
        logging.error(f"Error updating blog post: {e}")
        return jsonify({'message': str(e)}), 500

@blog_bp.route('/<blog_id>', methods=['DELETE'])
@token_required
def delete_blog_route(current_user, blog_id):
    """Supprime un article de blog."""
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Admin privileges required'}), 403
        
    try:
        if blog_service.delete_blog(blog_id):
            return jsonify({'message': 'Blog post deleted successfully'})
        return jsonify({'message': 'Blog post not found'}), 404
    except Exception as e:
        logging.error(f"Error deleting blog post: {e}")
        return jsonify({'message': str(e)}), 500
