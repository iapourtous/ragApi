"""
Script d'encodage de documents PDF pour l'application RAG API.

Ce script permet de traiter des fichiers PDF en extrayant et vectorisant leur contenu.
Il offre une interface utilisateur en ligne de commande pour sélectionner et configurer
le traitement des fichiers. Le traitement inclut l'extraction de texte, la correction OCR,
la vectorisation, et optionnellement l'extraction et la description d'images.
"""
import curses
import os
import json
import logging
import tempfile
from datetime import datetime
import fitz
import torch
from sentence_transformers import SentenceTransformer
from pathlib import Path

from app.models.files_book import FilesBook
from app.models.vllm_openai_model import VLLMOpenAIModel
from app.utils.ai_utils import correct_ocr_text
from app.utils.file_utils import save_processed_data
from app.utils.text_utils import del_pages_number
from app.pdf_aiEncode import extract_images_from_page

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='pdf_processing.log'
)

def correct_ocr_text_local(text, vllm_model):
    """Version locale de la fonction correct_ocr_text"""
    prompt = f"""En tant qu'expert en correction de textes OCR, corrige les erreurs potentielles dans le texte suivant 
tout en préservant son sens et sa structure. Retourne uniquement le texte corrigé, sans commentaires ni explications.

Texte à corriger:
{text}

Instructions:
- Corrige les erreurs d'OCR courantes (caractères mal reconnus, mots fusionnés ou séparés incorrectement)
- Préserve la mise en page et la structure du texte
- Conserve la ponctuation d'origine sauf si manifestement erronée
- Ne modifie pas le contenu sémantique
- Ne rajoute pas de contenu
"""
    try:
        corrected_text = vllm_model.generate_response(prompt)
        return corrected_text if corrected_text else text
    except Exception as e:
        logging.error(f"Erreur lors de la correction OCR: {e}")
        return text


class PDFProcessor:
    def __init__(self):
        self.model = None
        self.vllm_model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.initialize_models()
        
    def initialize_models(self):
        try:
            self.model = SentenceTransformer("intfloat/multilingual-e5-large", device=self.device)
            self.vllm_model = VLLMOpenAIModel()
            logging.info("Modèles chargés avec succès")
        except Exception as e:
            logging.error(f"Erreur lors du chargement des modèles : {e}")
            raise

    def process_page(self, page, doc, temp_dir, process_images=False):
        """Traite une seule page avec correction OCR et vectorisation"""
        try:
            # Extraction du texte et suppression des numéros de page
            page_text = page.get_text()
            page_text = del_pages_number(page_text)
            
            # Correction OCR
            try:
                corrected_text = correct_ocr_text_local(page_text, self.vllm_model)
                if not corrected_text:
                    corrected_text = page_text
                    logging.warning(f"Correction OCR échouée pour la page {page.number + 1}, utilisation du texte original")
            except Exception as e:
                logging.error(f"Erreur correction OCR page {page.number + 1}: {e}")
                corrected_text = page_text

            # Traitement des images si nécessaire
            if process_images:
                try:
                    images = extract_images_from_page(doc, page, temp_dir)
                    for image_path in images:
                        try:
                            image_description = self.vllm_model.generate_response(
                                image_path,
                                f"Décris cette image dans le contexte suivant:\n{corrected_text}"
                            )
                            if image_description:
                                corrected_text += f"\n\n### Description des illustrations\n{image_description}"
                        except Exception as e:
                            logging.error(f"Erreur description image page {page.number + 1}: {e}")
                except Exception as e:
                    logging.error(f"Erreur extraction images page {page.number + 1}: {e}")

            # Vectorisation du texte corrigé
            try:
                embedding = self.model.encode(corrected_text, convert_to_tensor=True, normalize_embeddings=True)
                return {
                    "pageNumber": page.number + 1,
                    "text": corrected_text,
                    "vector": embedding.tolist()
                }
            except Exception as e:
                logging.error(f"Erreur vectorisation page {page.number + 1}: {e}")
                return None

        except Exception as e:
            logging.error(f"Erreur traitement page {page.number + 1}: {e}")
            return None

    def process_file(self, pdf_path, output_dir, metadata):
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            db_path = os.path.join(output_dir, f"{base_name}.db")
            json_path = os.path.join(output_dir, f"{base_name}.json")
            
            book = FilesBook(file_name=base_name)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                doc = fitz.open(pdf_path)
                
                # Vérification de la plage de pages
                total_pages = doc.page_count
                begin = max(1, metadata['begin'])
                end = min(total_pages, metadata['end'])
                
                if begin > end or begin > total_pages or end < 1:
                    raise ValueError(f"Plage de pages invalide: {begin}-{end} (total: {total_pages})")
                
                # Initialisation des structures pour les descriptions
                page_descriptions = []
                page_vectors = []
                
                # Traitement page par page
                for page_num in range(begin - 1, end):
                    try:
                        page = doc[page_num]
                        processed_page = self.process_page(page, doc, temp_dir, metadata['illustration'])
                        
                        if processed_page:
                            page_descriptions.append({
                                'text': processed_page['text'],
                                'page_range': f"Page {processed_page['pageNumber']}",
                                'start_page': processed_page['pageNumber'],
                                'end_page': processed_page['pageNumber']
                            })
                            page_vectors.append(processed_page['vector'])
                            logging.info(f"Page {page_num + 1} traitée avec succès")
                        else:
                            logging.warning(f"Page {page_num + 1} ignorée suite à une erreur")
                    except Exception as e:
                        logging.error(f"Erreur traitement page {page_num + 1}: {e}")
                        continue

                if not page_descriptions:
                    raise ValueError("Aucune page n'a pu être traitée correctement")

                # Ajout du premier niveau de descriptions
                book.descriptions.append(page_descriptions)
                book.descriptions_vectorized.append(page_vectors)

                # Génération des niveaux supérieurs de description
                current_level = page_descriptions
                current_vectors = page_vectors

                while len(current_level) > 1:
                    next_level = []
                    next_vectors = []
                    
                    for i in range(0, len(current_level), 2):
                        texts = [current_level[i]['text']]
                        if i + 1 < len(current_level):
                            texts.append(current_level[i + 1]['text'])
                        
                        combined_text = "\n\n".join(texts)
                        try:
                            summary = self.vllm_model.generate_response(
                                combined_text,
                                "Génère un résumé cohérent et structuré de ce texte en 500 mots maximum."
                            )
                            
                            if not summary:
                                summary = combined_text
                            
                            start_page = current_level[i]['start_page']
                            end_page = current_level[i]['end_page'] if i + 1 >= len(current_level) else current_level[i + 1]['end_page']
                            
                            embedding = self.model.encode(summary, convert_to_tensor=True, normalize_embeddings=True)
                            
                            next_level.append({
                                'text': summary,
                                'page_range': f"Pages {start_page} à {end_page}",
                                'start_page': start_page,
                                'end_page': end_page
                            })
                            next_vectors.append(embedding.tolist())
                        except Exception as e:
                            logging.error(f"Erreur génération résumé niveau supérieur: {e}")
                            continue
                    
                    if next_level:
                        book.descriptions.append(next_level)
                        book.descriptions_vectorized.append(next_vectors)
                        current_level = next_level
                        current_vectors = next_vectors
                    else:
                        break

                # Définir la description finale
                if current_level and len(current_level) > 0:
                    book.description = current_level[0]['text']
                
                # Sauvegarder les fichiers
                try:
                    save_processed_data(db_path, book)
                    
                    metadata.update({
                        'processed_at': datetime.now().isoformat(),
                        'total_pages': end - begin + 1,
                        'has_illustrations': metadata['illustration'],
                        'file_name': base_name,
                        'db_path': db_path,
                        'pages_processed': len(page_descriptions)
                    })
                    
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    logging.error(f"Erreur sauvegarde fichiers: {e}")
                    raise
                
                return True
                
        except Exception as e:
            logging.error(f"Erreur traitement fichier : {e}")
            return False
class PDFProcessorUI:
    def __init__(self):
        self.processor = PDFProcessor()
        
    def display_menu(self, stdscr, options, title, selected=0):
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        
        title_y = 2
        title_x = w//2 - len(title)//2
        stdscr.addstr(title_y, title_x, title)
        
        for idx, option in enumerate(options):
            y = title_y + 2 + idx
            x = w//2 - len(option)//2
            if idx == selected:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(y, x, option)
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(y, x, option)
        
        stdscr.refresh()

    def get_input(self, stdscr, prompt, y):
        h, w = stdscr.getmaxyx()
        stdscr.addstr(y, 2, prompt)
        stdscr.refresh()
        curses.echo()
        value = stdscr.getstr(y, len(prompt) + 3, 60).decode('utf-8')
        curses.noecho()
        return value

    def display_status(self, stdscr, message, y, error=False):
        stdscr.addstr(y, 2, message, curses.A_REVERSE if error else curses.A_NORMAL)
        stdscr.refresh()

    def run(self, stdscr):
        curses.curs_set(0)
        current_dir = os.getcwd()
        
        while True:
            pdf_files = [f for f in os.listdir(current_dir) if f.endswith('.pdf')]
            options = pdf_files + ['[Changer de répertoire]', '[Quitter]']
            
            selected = 0
            while True:
                self.display_menu(stdscr, options, f"Répertoire actuel: {current_dir}", selected)
                key = stdscr.getch()
                
                if key == curses.KEY_UP and selected > 0:
                    selected -= 1
                elif key == curses.KEY_DOWN and selected < len(options) - 1:
                    selected += 1
                elif key == 10:  # Enter
                    break
            
            if options[selected] == '[Quitter]':
                break
            elif options[selected] == '[Changer de répertoire]':
                stdscr.clear()
                new_dir = self.get_input(stdscr, "Nouveau répertoire: ", 2)
                if os.path.isdir(new_dir):
                    current_dir = new_dir
                continue
            
            pdf_file = options[selected]
            stdscr.clear()
            
            try:
                # Vérification du PDF
                pdf_path = os.path.join(current_dir, pdf_file)
                doc = fitz.open(pdf_path)
                total_pages = doc.page_count
                doc.close()
                
                self.display_status(stdscr, f"Pages totales dans le PDF: {total_pages}", 1)
                
                metadata = {
                    'title': self.get_input(stdscr, "Titre: ", 3),
                    'category': self.get_input(stdscr, "Catégorie: ", 5),
                    'directory': self.get_input(stdscr, "Répertoire de sortie: ", 7),
                    'begin': int(self.get_input(stdscr, "Page de début: ", 9)),
                    'end': int(self.get_input(stdscr, "Page de fin: ", 11)),
                    'illustration': self.get_input(stdscr, "Traiter les images (o/n): ", 13).lower() == 'o',
                    'proprietary': 'public',
                    'created_at': datetime.now().isoformat()
                }
                
                output_dir = os.path.join(current_dir, metadata['directory'])
                
                self.display_status(stdscr, "Traitement en cours...", 15)
                
                success = self.processor.process_file(pdf_path, output_dir, metadata)
                
                if success:
                    self.display_status(stdscr, "Traitement terminé avec succès!", 17)
                else:
                    self.display_status(stdscr, "Erreur lors du traitement!", 17, error=True)
                
            except ValueError as ve:
                self.display_status(stdscr, f"Erreur de validation: {str(ve)}", 17, error=True)
            except Exception as e:
                self.display_status(stdscr, f"Erreur: {str(e)}", 17, error=True)
            
            self.display_status(stdscr, "Appuyez sur une touche pour continuer...", 19)
            stdscr.getch()

def main():
    ui = PDFProcessorUI()
    curses.wrapper(ui.run)

if __name__ == "__main__":
    main()