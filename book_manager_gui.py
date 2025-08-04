#!/usr/bin/env python3
"""
Utilitaire graphique tkinter pour ajouter des livres à l'API RAG.

Cette application fournit une interface graphique intuitive pour :
- Téléverser des fichiers PDF
- Saisir les métadonnées du livre (titre, auteur, description, etc.)
- Configurer les options de traitement
- Téléverser une image de couverture
- Prévisualiser le PDF
- Communiquer avec l'API RAG pour créer le livre
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import requests
from pathlib import Path
import threading
from PIL import Image, ImageTk
import tempfile


class BookManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestionnaire de Livres - RAG API")
        self.root.geometry("800x900")
        self.root.resizable(True, True)
        
        # Configuration de l'API
        self.api_base_url = "http://localhost:8081"
        
        # Variables pour les fichiers
        self.pdf_file_path = None
        self.cover_image_path = None
        self.preview_image = None
        
        # Variables tkinter
        self.setup_variables()
        
        # Catégories prédéfinies
        self.categories = [
            "Fiction", "Philosophie", "Programmation", "Religion", 
            "Psychologie", "Economie", "Administratif", "Restauration"
        ]
        
        # Interface utilisateur
        self.setup_ui()
    
    def setup_variables(self):
        """Initialise les variables tkinter."""
        self.title_var = tk.StringVar()
        self.author_var = tk.StringVar()
        self.description_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.subcategory_var = tk.StringVar()
        self.edition_var = tk.StringVar()
        self.public_var = tk.BooleanVar()
        self.illustration_var = tk.BooleanVar(value=False)
        self.begin_page_var = tk.IntVar(value=0)
        self.end_page_var = tk.IntVar(value=0)
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Prêt")
    
    def setup_ui(self):
        """Configure l'interface utilisateur."""
        # Frame principal avec scrollbar
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Titre de l'application
        title_label = ttk.Label(main_frame, text="Gestionnaire de Livres RAG", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Section 1: Fichier PDF
        self.create_pdf_section(main_frame)
        
        # Section 2: Métadonnées
        self.create_metadata_section(main_frame)
        
        # Section 3: Options de traitement
        self.create_processing_section(main_frame)
        
        # Section 4: Image de couverture
        self.create_cover_section(main_frame)
        
        # Section 5: Prévisualisation
        self.create_preview_section(main_frame)
        
        # Section 6: Actions
        self.create_action_section(main_frame)
        
        # Barre de statut
        self.create_status_section(main_frame)
    
    def create_pdf_section(self, parent):
        """Crée la section de sélection du fichier PDF."""
        pdf_frame = ttk.LabelFrame(parent, text="📄 Fichier PDF", padding=10)
        pdf_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Frame pour le bouton et le label
        file_frame = ttk.Frame(pdf_frame)
        file_frame.pack(fill=tk.X)
        
        self.pdf_button = ttk.Button(file_frame, text="Sélectionner PDF", 
                                    command=self.select_pdf_file)
        self.pdf_button.pack(side=tk.LEFT)
        
        self.pdf_label = ttk.Label(file_frame, text="Aucun fichier sélectionné", 
                                  foreground="gray")
        self.pdf_label.pack(side=tk.LEFT, padx=(10, 0))
    
    def create_metadata_section(self, parent):
        """Crée la section des métadonnées."""
        meta_frame = ttk.LabelFrame(parent, text="📝 Métadonnées", padding=10)
        meta_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Grille pour organiser les champs
        meta_frame.grid_columnconfigure(1, weight=1)
        
        # Titre (requis)
        ttk.Label(meta_frame, text="Titre *:").grid(row=0, column=0, sticky="w", pady=2)
        title_entry = ttk.Entry(meta_frame, textvariable=self.title_var, width=60)
        title_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=2)
        
        # Auteur (requis)
        ttk.Label(meta_frame, text="Auteur *:").grid(row=1, column=0, sticky="w", pady=2)
        author_entry = ttk.Entry(meta_frame, textvariable=self.author_var, width=60)
        author_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=2)
        
        # Édition
        ttk.Label(meta_frame, text="Édition:").grid(row=2, column=0, sticky="w", pady=2)
        edition_entry = ttk.Entry(meta_frame, textvariable=self.edition_var, width=60)
        edition_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=2)
        
        # Catégorie
        ttk.Label(meta_frame, text="Catégorie:").grid(row=3, column=0, sticky="w", pady=2)
        category_combo = ttk.Combobox(meta_frame, textvariable=self.category_var, 
                                     values=self.categories, width=58)
        category_combo.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=2)
        
        # Sous-catégorie
        ttk.Label(meta_frame, text="Sous-catégorie:").grid(row=4, column=0, sticky="w", pady=2)
        subcategory_entry = ttk.Entry(meta_frame, textvariable=self.subcategory_var, width=60)
        subcategory_entry.grid(row=4, column=1, sticky="ew", padx=(10, 0), pady=2)
        
        # Description
        ttk.Label(meta_frame, text="Description:").grid(row=5, column=0, sticky="nw", pady=2)
        desc_frame = ttk.Frame(meta_frame)
        desc_frame.grid(row=5, column=1, sticky="ew", padx=(10, 0), pady=2)
        desc_frame.grid_columnconfigure(0, weight=1)
        
        self.description_text = scrolledtext.ScrolledText(desc_frame, height=4, width=50)
        self.description_text.grid(row=0, column=0, sticky="ew")
        
        # Bouton pour générer la description automatiquement
        ttk.Button(desc_frame, text="Générer auto", 
                  command=self.generate_description).grid(row=1, column=0, sticky="e", pady=(5, 0))
        
        # Public
        public_check = ttk.Checkbutton(meta_frame, text="Livre public", 
                                      variable=self.public_var)
        public_check.grid(row=6, column=1, sticky="w", padx=(10, 0), pady=2)
    
    def create_processing_section(self, parent):
        """Crée la section des options de traitement."""
        proc_frame = ttk.LabelFrame(parent, text="⚙️ Options de traitement", padding=10)
        proc_frame.pack(fill=tk.X, pady=(0, 10))
        
        proc_frame.grid_columnconfigure(1, weight=1)
        proc_frame.grid_columnconfigure(3, weight=1)
        
        # Traiter les illustrations
        illustration_check = ttk.Checkbutton(proc_frame, text="Traiter les illustrations", 
                                           variable=self.illustration_var)
        illustration_check.grid(row=0, column=0, columnspan=4, sticky="w", pady=2)
        
        # Pages début/fin
        ttk.Label(proc_frame, text="Page début:").grid(row=1, column=0, sticky="w", pady=2)
        begin_entry = ttk.Entry(proc_frame, textvariable=self.begin_page_var, width=10)
        begin_entry.grid(row=1, column=1, sticky="w", padx=(10, 20), pady=2)
        
        ttk.Label(proc_frame, text="Page fin:").grid(row=1, column=2, sticky="w", pady=2)
        end_entry = ttk.Entry(proc_frame, textvariable=self.end_page_var, width=10)
        end_entry.grid(row=1, column=3, sticky="w", padx=(10, 0), pady=2)
        
        # Info sur les pages
        info_label = ttk.Label(proc_frame, text="(0 = traiter tout le document)", 
                              foreground="gray", font=("Arial", 8))
        info_label.grid(row=2, column=0, columnspan=4, sticky="w", pady=2)
    
    def create_cover_section(self, parent):
        """Crée la section de l'image de couverture."""
        cover_frame = ttk.LabelFrame(parent, text="🖼️ Image de couverture (optionnel)", padding=10)
        cover_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Frame pour le bouton et l'info
        cover_button_frame = ttk.Frame(cover_frame)
        cover_button_frame.pack(fill=tk.X)
        
        self.cover_button = ttk.Button(cover_button_frame, text="Sélectionner image", 
                                      command=self.select_cover_image)
        self.cover_button.pack(side=tk.LEFT)
        
        self.cover_label = ttk.Label(cover_button_frame, text="Aucune image sélectionnée", 
                                    foreground="gray")
        self.cover_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Frame pour la prévisualisation de l'image
        self.cover_preview_frame = ttk.Frame(cover_frame)
        self.cover_preview_frame.pack(fill=tk.X, pady=(10, 0))
    
    def create_preview_section(self, parent):
        """Crée la section de prévisualisation du PDF."""
        preview_frame = ttk.LabelFrame(parent, text="👁️ Prévisualisation PDF", padding=10)
        preview_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Bouton pour générer la prévisualisation
        self.preview_button = ttk.Button(preview_frame, text="Générer prévisualisation", 
                                        command=self.generate_preview, state="disabled")
        self.preview_button.pack()
        
        # Frame pour l'image de prévisualisation
        self.pdf_preview_frame = ttk.Frame(preview_frame)
        self.pdf_preview_frame.pack(fill=tk.X, pady=(10, 0))
    
    def create_action_section(self, parent):
        """Crée la section des boutons d'action."""
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Boutons
        ttk.Button(action_frame, text="Annuler", 
                  command=self.clear_form).pack(side=tk.LEFT)
        
        ttk.Button(action_frame, text="Valider et créer", 
                  command=self.create_book, 
                  style="Accent.TButton").pack(side=tk.RIGHT)
    
    def create_status_section(self, parent):
        """Crée la barre de statut."""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Barre de progression
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, 
                                           maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # Label de statut
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.pack(anchor="w")
    
    def select_pdf_file(self):
        """Sélectionne un fichier PDF."""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier PDF",
            filetypes=[("Fichiers PDF", "*.pdf"), ("Tous les fichiers", "*.*")]
        )
        
        if file_path:
            self.pdf_file_path = file_path
            filename = os.path.basename(file_path)
            self.pdf_label.config(text=filename, foreground="black")
            self.preview_button.config(state="normal")
            
            # Auto-remplir le titre si vide
            if not self.title_var.get():
                title = os.path.splitext(filename)[0]
                self.title_var.set(title)
    
    def select_cover_image(self):
        """Sélectionne une image de couverture."""
        file_path = filedialog.askopenfilename(
            title="Sélectionner une image de couverture",
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.gif *.bmp *.webp"),
                ("Tous les fichiers", "*.*")
            ]
        )
        
        if file_path:
            self.cover_image_path = file_path
            filename = os.path.basename(file_path)
            self.cover_label.config(text=filename, foreground="black")
            self.show_cover_preview(file_path)
    
    def show_cover_preview(self, image_path):
        """Affiche la prévisualisation de l'image de couverture."""
        try:
            # Nettoyer l'ancienne prévisualisation
            for widget in self.cover_preview_frame.winfo_children():
                widget.destroy()
            
            # Charger et redimensionner l'image
            image = Image.open(image_path)
            image.thumbnail((200, 200), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            # Afficher l'image
            label = ttk.Label(self.cover_preview_frame, image=photo)
            label.image = photo  # Garder une référence
            label.pack()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger l'image : {e}")
    
    def generate_preview(self):
        """Génère une prévisualisation de la première page du PDF."""
        if not self.pdf_file_path:
            messagebox.showwarning("Avertissement", "Veuillez d'abord sélectionner un fichier PDF.")
            return
        
        self.status_var.set("Génération de la prévisualisation...")
        self.progress_var.set(50)
        
        def preview_thread():
            try:
                # Appel à l'API pour générer la prévisualisation
                data = {
                    "pdf_path": os.path.basename(self.pdf_file_path),
                    "page_number": 0,
                    "max_width": 400
                }
                
                response = requests.post(f"{self.api_base_url}/pdf/generate-preview", 
                                       json=data, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    image_url = self.api_base_url + result.get('image_path', '')
                    
                    # Télécharger et afficher l'image
                    img_response = requests.get(image_url, timeout=10)
                    if img_response.status_code == 200:
                        # Sauvegarder temporairement l'image
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.webp') as tmp_file:
                            tmp_file.write(img_response.content)
                            tmp_path = tmp_file.name
                        
                        # Afficher dans l'interface
                        self.root.after(0, lambda: self.show_pdf_preview(tmp_path))
                    else:
                        self.root.after(0, lambda: messagebox.showerror(
                            "Erreur", "Impossible de télécharger l'image de prévisualisation."))
                else:
                    error_msg = response.json().get('error', 'Erreur inconnue')
                    self.root.after(0, lambda: messagebox.showerror(
                        "Erreur API", f"Erreur lors de la génération : {error_msg}"))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Erreur", f"Erreur lors de la génération de la prévisualisation : {e}"))
            finally:
                self.root.after(0, lambda: (
                    self.progress_var.set(0),
                    self.status_var.set("Prêt")
                ))
        
        threading.Thread(target=preview_thread, daemon=True).start()
    
    def show_pdf_preview(self, image_path):
        """Affiche la prévisualisation du PDF."""
        try:
            # Nettoyer l'ancienne prévisualisation
            for widget in self.pdf_preview_frame.winfo_children():
                widget.destroy()
            
            # Charger et afficher l'image
            image = Image.open(image_path)
            image.thumbnail((300, 400), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            label = ttk.Label(self.pdf_preview_frame, image=photo)
            label.image = photo  # Garder une référence
            label.pack()
            
            # Nettoyer le fichier temporaire
            os.unlink(image_path)
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'afficher la prévisualisation : {e}")
    
    def generate_description(self):
        """Génère automatiquement une description du livre."""
        if not self.pdf_file_path:
            messagebox.showwarning("Avertissement", "Veuillez d'abord sélectionner un fichier PDF.")
            return
        
        self.status_var.set("Génération de la description...")
        self.progress_var.set(30)
        
        def description_thread():
            try:
                data = {
                    "pdf_files": [os.path.basename(self.pdf_file_path)],
                    "context": "Générer une description courte et engageante de ce livre."
                }
                
                response = requests.post(f"{self.api_base_url}/book/generate_description", 
                                       json=data, timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    description = result.get('description', '')
                    
                    # Mettre à jour l'interface
                    self.root.after(0, lambda: self.description_text.delete(1.0, tk.END))
                    self.root.after(0, lambda: self.description_text.insert(1.0, description))
                else:
                    error_msg = response.json().get('error', 'Erreur inconnue')
                    self.root.after(0, lambda: messagebox.showerror(
                        "Erreur API", f"Erreur lors de la génération : {error_msg}"))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Erreur", f"Erreur lors de la génération de la description : {e}"))
            finally:
                self.root.after(0, lambda: (
                    self.progress_var.set(0),
                    self.status_var.set("Prêt")
                ))
        
        threading.Thread(target=description_thread, daemon=True).start()
    
    def validate_form(self):
        """Valide le formulaire avant soumission."""
        errors = []
        
        if not self.pdf_file_path:
            errors.append("Veuillez sélectionner un fichier PDF.")
        
        if not self.title_var.get().strip():
            errors.append("Le titre est requis.")
        
        if not self.author_var.get().strip():
            errors.append("L'auteur est requis.")
        
        if self.begin_page_var.get() < 0:
            errors.append("La page de début doit être >= 0.")
        
        if self.end_page_var.get() < 0:
            errors.append("La page de fin doit être >= 0.")
        
        if self.begin_page_var.get() > 0 and self.end_page_var.get() > 0:
            if self.begin_page_var.get() >= self.end_page_var.get():
                errors.append("La page de début doit être inférieure à la page de fin.")
        
        return errors
    
    def create_book(self):
        """Crée le livre via l'API."""
        # Validation
        errors = self.validate_form()
        if errors:
            messagebox.showerror("Erreurs de validation", "\n".join(errors))
            return
        
        self.status_var.set("Création du livre en cours...")
        self.progress_var.set(0)
        
        def create_thread():
            try:
                # Préparer les données du formulaire
                form_data = {
                    'title': self.title_var.get().strip(),
                    'author': self.author_var.get().strip(),
                    'description': self.description_text.get(1.0, tk.END).strip(),
                    'edition': self.edition_var.get().strip(),
                    'category': self.category_var.get().strip(),
                    'subcategory': self.subcategory_var.get().strip(),
                    'directory': self.category_var.get().strip() or 'default',
                    'proprietary': 'public',
                    'public': str(self.public_var.get()).lower(),
                    'illustration': str(self.illustration_var.get()).lower(),
                    'begin': str(self.begin_page_var.get()),
                    'end': str(self.end_page_var.get())
                }
                
                print(f"DEBUG: Form data = {form_data}")
                print(f"DEBUG: PDF file = {self.pdf_file_path}")
                print(f"DEBUG: Cover image = {self.cover_image_path}")
                
                # Préparer les fichiers pour l'upload
                files = {}
                
                # Fichier PDF
                files['pdf_file'] = (os.path.basename(self.pdf_file_path), 
                                   open(self.pdf_file_path, 'rb'), 'application/pdf')
                
                # Image de couverture (si présente)
                if self.cover_image_path:
                    files['cover_image'] = (os.path.basename(self.cover_image_path), 
                                          open(self.cover_image_path, 'rb'), 'image/*')
                
                self.root.after(0, lambda: self.progress_var.set(25))
                
                # Appel à l'API
                response = requests.post(
                    f"{self.api_base_url}/book/",
                    data=form_data,
                    files=files,
                    timeout=120
                )
                
                # Fermer les fichiers
                for file_tuple in files.values():
                    if hasattr(file_tuple[1], 'close'):
                        file_tuple[1].close()
                
                self.root.after(0, lambda: self.progress_var.set(75))
                
                print(f"DEBUG: Response status = {response.status_code}")
                print(f"DEBUG: Response text = {response.text[:500]}")
                
                if response.status_code == 201:
                    result = response.json()
                    book_id = result.get('_id', 'Inconnu')
                    
                    self.root.after(0, lambda: (
                        self.progress_var.set(100),
                        self.status_var.set("Livre créé avec succès!"),
                        messagebox.showinfo("Succès", 
                                          f"Livre créé avec succès!\nID: {book_id}\n\n"
                                          "Le traitement du PDF se fait en arrière-plan.")
                    ))
                    
                    # Optionnel : vider le formulaire
                    self.root.after(1000, self.clear_form)
                
                else:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('error', 'Erreur inconnue')
                    except:
                        error_msg = f"Erreur HTTP {response.status_code}: {response.text[:200]}"
                    
                    print(f"DEBUG: Error = {error_msg}")
                    self.root.after(0, lambda: messagebox.showerror(
                        "Erreur API", f"Erreur lors de la création : {error_msg}"))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Erreur", f"Erreur lors de la création du livre : {e}"))
            finally:
                self.root.after(0, lambda: (
                    self.progress_var.set(0),
                    self.status_var.set("Prêt")
                ))
        
        threading.Thread(target=create_thread, daemon=True).start()
    
    def clear_form(self):
        """Efface le formulaire."""
        # Variables texte
        self.title_var.set("")
        self.author_var.set("")
        self.description_text.delete(1.0, tk.END)
        self.category_var.set("")
        self.subcategory_var.set("")
        self.edition_var.set("")
        
        # Variables booléennes
        self.public_var.set(False)
        self.illustration_var.set(False)
        
        # Variables numériques
        self.begin_page_var.set(0)
        self.end_page_var.set(0)
        
        # Fichiers
        self.pdf_file_path = None
        self.cover_image_path = None
        
        # Labels
        self.pdf_label.config(text="Aucun fichier sélectionné", foreground="gray")
        self.cover_label.config(text="Aucune image sélectionnée", foreground="gray")
        
        # Boutons
        self.preview_button.config(state="disabled")
        
        # Prévisualisations
        for widget in self.cover_preview_frame.winfo_children():
            widget.destroy()
        for widget in self.pdf_preview_frame.winfo_children():
            widget.destroy()
        
        # Statut
        self.status_var.set("Prêt")
        self.progress_var.set(0)


def main():
    """Point d'entrée principal de l'application."""
    root = tk.Tk()
    
    # Configuration du style
    style = ttk.Style()
    style.theme_use('clam')  # Thème moderne
    
    # Style pour le bouton principal
    style.configure("Accent.TButton", foreground="white", background="#0078d4")
    
    app = BookManagerGUI(root)
    
    # Configuration de la fermeture
    def on_closing():
        if messagebox.askokcancel("Quitter", "Voulez-vous vraiment quitter l'application?"):
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Démarrage de l'application
    root.mainloop()


if __name__ == "__main__":
    main()