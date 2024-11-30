from datetime import datetime
from PIL import Image
import tempfile
import logging
import base64
import os

import fitz



def convert_pdf_page_to_image(pdf_path, page_number=0, max_width=400, output_format='webp'):
    """
    Convertit une page de PDF en image avec redimensionnement.
    
    Args:
        pdf_path (str): Chemin vers le fichier PDF
        page_number (int): Numéro de la page à convertir (0-based)
        max_width (int): Largeur maximale de l'image de sortie
        output_format (str): Format de sortie de l'image ('webp' par défaut)
    
    Returns:
        tuple: (nom_fichier, chemin_complet) ou (None, None) en cas d'erreur
    """
    try:
        # Ouvrir le PDF
        doc = fitz.open(pdf_path)
        if page_number >= len(doc):
            raise ValueError(f"Le PDF ne contient pas de page {page_number + 1}")

        # Obtenir la page
        page = doc[page_number]
        
        # Augmenter la résolution du rendu
        zoom = 2  # augmente la qualité
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Convertir en image PIL
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Redimensionner en conservant le ratio
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
        
        # Générer un nom de fichier unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cover_{timestamp}.{output_format}"
        
        return filename, img
        
    except Exception as e:
        logging.error(f"Erreur lors de la conversion PDF en image : {e}")
        return None, None
    finally:
        if 'doc' in locals():
            doc.close()
            
def resize_image(self, image_path, max_size=800):
    """Redimensionne l'image tout en conservant le ratio d'aspect."""
    try:
        with Image.open(image_path) as img:
            img.thumbnail((max_size, max_size))
            # Utiliser un fichier temporaire pour l'image résizée
            temp_resized = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            img.save(temp_resized.name)
            logging.debug(f"Image redimensionnée sauvegardée temporairement à '{temp_resized.name}'.")
            return temp_resized.name
    except Exception as e:
        logging.error(f"Erreur lors du redimensionnement de l'image {image_path}: {e}")
        return None

def encode_image(self, image_path):
    """Encode l'image en base64."""
    resized_image_path = self.resize_image(image_path)
    if not resized_image_path:
        logging.error("Échec du redimensionnement de l'image. Encodage annulé.")
        return None

    try:
        with open(resized_image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            logging.debug(f"Image encodée en base64 à partir de '{resized_image_path}'.")
    except FileNotFoundError:
        logging.error(f"Erreur : Le fichier {resized_image_path} n'a pas été trouvé.")
        encoded_image = None
    except Exception as e:
        logging.error(f"Erreur lors de l'encodage de l'image {resized_image_path}: {e}")
        encoded_image = None
    finally:
        # Supprimer l'image résizée temporaire
        try:
            os.remove(resized_image_path)
            logging.debug(f"Image résizée temporaire '{resized_image_path}' supprimée.")
        except OSError as e:
            logging.error(f"Erreur lors de la suppression de l'image résizée temporaire '{resized_image_path}': {e}")
    
    return encoded_image    
