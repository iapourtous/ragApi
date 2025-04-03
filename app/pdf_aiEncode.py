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