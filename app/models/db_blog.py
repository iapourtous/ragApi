from datetime import datetime
import re

class DBBlog:
    """
    Représente un article de blog dans la base de données.
    
    Attributes:
        _id (str): Identifiant unique de l'article
        title (str): Titre de l'article
        summary (str): Résumé de l'article
        content (str): Contenu complet de l'article
        author (str): Nom de l'auteur
        created_at (datetime): Date de création
        updated_at (datetime): Date de dernière modification
        is_visible (bool): Visibilité de l'article
        category (str): Catégorie de l'article
        image_url (str): URL de l'image d'illustration
        pretty_url (str): URL conviviale générée à partir du titre
    """

    def __init__(self, title, summary, content, author, category, image_url=None,
                 is_visible=True, created_at=None, updated_at=None, _id=None):
        self._id = _id
        self.title = title
        self.summary = summary
        self.content = content
        self.author = author
        self.category = category
        self.image_url = image_url
        self.is_visible = is_visible
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.pretty_url = self._generate_pretty_url(title)

    @staticmethod
    def _generate_pretty_url(title):
        """Génère une URL conviviale à partir du titre."""
        # Convertit en minuscules et remplace les espaces par des tirets
        pretty_url = title.lower()
        # Supprime les caractères spéciaux
        pretty_url = re.sub(r'[^a-z0-9\s-]', '', pretty_url)
        # Remplace les espaces par des tirets
        pretty_url = re.sub(r'\s+', '-', pretty_url)
        # Supprime les tirets multiples
        pretty_url = re.sub(r'-+', '-', pretty_url)
        return pretty_url.strip('-')

    @staticmethod
    def from_dict(data):
        """Crée une instance de DBBlog à partir d'un dictionnaire."""
        return DBBlog(
            _id=data.get('_id'),
            title=data.get('title'),
            summary=data.get('summary'),
            content=data.get('content'),
            author=data.get('author'),
            category=data.get('category'),
            image_url=data.get('image_url'),
            is_visible=data.get('is_visible', True),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    def to_dict(self):
        """Convertit l'instance en dictionnaire."""
        data = {
            'title': self.title,
            'summary': self.summary,
            'content': self.content,
            'author': self.author,
            'category': self.category,
            'image_url': self.image_url,
            'is_visible': self.is_visible,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'pretty_url': self.pretty_url
        }
        if self._id:
            data['_id'] = self._id
        return data