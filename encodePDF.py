# pdf_processor.py
import curses
import os
import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
import fitz
import torch
from sentence_transformers import SentenceTransformer

from app.models.files_book import FilesBook
from app.models.vllm_openai_model import VLLMOpenAIModel
from app.utils.ai_utils import correct_ocr_text, generate_overall_description
from app.utils.file_utils import save_processed_data
from app.background_tasks import extract_images_from_page

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='pdf_processing.log'
)

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

    def process_file(self, pdf_path, output_dir, metadata):
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            db_path = os.path.join(output_dir, f"{base_name}.db")
            json_path = os.path.join(output_dir, f"{base_name}.json")
            
            book = FilesBook(file_name=base_name)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                doc = fitz.open(pdf_path)
                
                corrected_pages = []
                for page_num in range(metadata['begin'] - 1, metadata['end']):
                    page = doc[page_num]
                    page_text = page.get_text()
                    
                    # Correction OCR avec vLLM
                    corrected_text = correct_ocr_text(page_text, self.vllm_model)
                    
                    # Traitement des images si activé
                    if metadata['illustration']:
                        images = extract_images_from_page(doc, page, temp_dir)
                        if images:
                            for image_path in images:
                                try:
                                    image_description = self.vllm_model.generate_response(
                                        image_path,
                                        f"Décris cette image dans le contexte suivant:\n{corrected_text}"
                                    )
                                    if image_description:
                                        corrected_text += f"\n\n### Description des illustrations\n{image_description}"
                                except Exception as e:
                                    logging.error(f"Erreur description image : {e}")
                    
                    corrected_pages.append({
                        "pageNumber": page_num + 1,
                        "text": corrected_text
                    })
                
                # Génération des descriptions hiérarchiques
                book.description, book.descriptions, book.descriptions_vectorized = generate_overall_description(
                    corrected_pages,
                    self.model,
                    partial_file=None,
                    book=book
                )
                
                # Sauvegarder les fichiers
                save_processed_data(db_path, book)
                
                metadata.update({
                    'processed_at': datetime.now().isoformat(),
                    'total_pages': metadata['end'] - metadata['begin'] + 1,
                    'has_illustrations': metadata['illustration'],
                    'file_name': base_name,
                    'db_path': db_path
                })
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=4)
                
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
            metadata = {
                'title': self.get_input(stdscr, "Titre: ", 2),
                'category': self.get_input(stdscr, "Catégorie: ", 4),
                'directory': self.get_input(stdscr, "Répertoire de sortie: ", 6),
                'begin': int(self.get_input(stdscr, "Page de début: ", 8)),
                'end': int(self.get_input(stdscr, "Page de fin: ", 10)),
                'illustration': self.get_input(stdscr, "Traiter les images (o/n): ", 12).lower() == 'o',
                'proprietary': 'public',  # Valeur par défaut
                'created_at': datetime.now().isoformat()
            }
            
            pdf_path = os.path.join(current_dir, pdf_file)
            output_dir = os.path.join(current_dir, metadata['directory'])
            
            stdscr.addstr(14, 2, "Traitement en cours...")
            stdscr.refresh()
            
            success = self.processor.process_file(pdf_path, output_dir, metadata)
            
            if success:
                stdscr.addstr(16, 2, "Traitement terminé avec succès!")
            else:
                stdscr.addstr(16, 2, "Erreur lors du traitement!")
            
            stdscr.addstr(18, 2, "Appuyez sur une touche pour continuer...")
            stdscr.refresh()
            stdscr.getch()

def main():
    ui = PDFProcessorUI()
    curses.wrapper(ui.run)

if __name__ == "__main__":
    main()