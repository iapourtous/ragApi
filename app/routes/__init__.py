from flask import Blueprint
from flask_cors import CORS
from .auth_routes import auth_bp
from .blog_routes import blog_bp
from .book_routes import book_bp
from .pdf_routes import pdf_bp
from .user_routes import user_bp
from .contact_routes import contact_bp

def init_routes(app):
    """Initialize all route blueprints"""

    # Enregistrer les blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(blog_bp, url_prefix='/blog')
    app.register_blueprint(book_bp, url_prefix='/books')
    app.register_blueprint(pdf_bp, url_prefix='/pdf')
    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(contact_bp, url_prefix='/contact')