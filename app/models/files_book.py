"""
Module de modèle de données pour les fichiers de livres traités dans l'application RAG API.

Ce module définit la classe FilesBook qui représente les données enrichies d'un livre
après son traitement. Il gère le stockage des contenus textuels, des descriptions, des
embeddings vectoriels et des métadonnées associées, permettant leur utilisation efficace
dans le pipeline de recherche et d'analyse.
"""

class FilesBook:
    """
    Modèle représentant les données volumineuses d'un livre, incluant les vecteurs, textes et descriptions.
    
    Cette classe gère le stockage et la manipulation des données volumineuses associées à un livre,
    notamment les pages, les résumés, les descriptions et leurs représentations vectorielles.
    
    Attributes:
        file_name (str): Nom du fichier associé au livre
        pages (list): Liste des pages du livre avec leur contenu
        summaries (list): Liste des résumés générés pour le livre
        description (str): Description générale du livre
        descriptions (list): Liste hiérarchique des descriptions du livre
        descriptions_vectorized (list): Liste des vecteurs correspondant aux descriptions
    """

    def __init__(self, file_name, pages=None, summaries=None, description=None,
                 descriptions=None, descriptions_vectorized=None):
        """
        Initialise une nouvelle instance de FilesBook.

        Args:
            file_name (str): Nom du fichier associé au livre
            pages (list, optional): Liste des pages du livre. Defaults to None.
            summaries (list, optional): Liste des résumés. Defaults to None.
            description (str, optional): Description générale du livre. Defaults to None.
            descriptions (list, optional): Liste des descriptions. Defaults to None.
            descriptions_vectorized (list, optional): Liste des vecteurs des descriptions. Defaults to None.
        """
        self.file_name = file_name
        self.pages = pages or []
        self.summaries = summaries or []
        self.description = description
        self.descriptions = descriptions or []
        self.descriptions_vectorized = descriptions_vectorized or []

    @staticmethod
    def from_dict(data):
        """
        Crée une instance de FilesBook à partir d'un dictionnaire.

        Cette méthode permet de désérialiser les données d'un livre stockées
        sous forme de dictionnaire pour créer une nouvelle instance de FilesBook.

        Args:
            data (dict): Dictionnaire contenant les données du livre avec les clés suivantes :
                - fileName (str): Nom du fichier
                - pages (list): Liste des pages
                - summaries (list): Liste des résumés
                - description (str): Description générale
                - descriptions (list): Liste des descriptions
                - descriptionsVectorized (list): Liste des vecteurs

        Returns:
            FilesBook: Nouvelle instance créée à partir des données
        """
        return FilesBook(
            file_name=data.get('fileName'),
            pages=data.get('pages', []),
            summaries=data.get('summaries', []),
            description=data.get('description'),
            descriptions=data.get('descriptions', []),
            descriptions_vectorized=data.get('descriptionsVectorized', [])
        )

    def to_dict(self):
        """
        Convertit l'instance en dictionnaire.

        Cette méthode sérialise toutes les données du livre en un format
        approprié pour le stockage ou la transmission.

        Returns:
            dict: Dictionnaire contenant toutes les données du livre avec les clés :
                - fileName (str): Nom du fichier
                - pages (list): Liste des pages
                - summaries (list): Liste des résumés
                - description (str): Description générale
                - descriptions (list): Liste des descriptions
                - descriptionsVectorized (list): Liste des vecteurs
        """
        return {
            'fileName': self.file_name,
            'pages': self.pages,
            'summaries': self.summaries,
            'description': self.description,
            'descriptions': self.descriptions,
            'descriptionsVectorized': self.descriptions_vectorized
        }