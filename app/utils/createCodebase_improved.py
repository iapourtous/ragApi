import os
import re
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from openai import OpenAI

class CodeBaseGenerator:
    def __init__(self, root):
        """Interface graphique pour générer une documentation filtrée par LLM"""
        self.root = root
        self.root.title("CodeBase Generator")
        self.root.geometry("900x700")

        # Initialisation du client OpenAI
        self.client = OpenAI(
            api_key="EMPTY",
            base_url="http://localhost:8000/v1",
        )
        
        self.selected_dir = tk.StringVar()
        self.user_query = tk.StringVar()
        
        # Dictionnaire de la base de code indexée
        self.project_index = {}
        
        # Variable pour le résultat final
        self.final_output = ""

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Sélection du dossier
        ttk.Button(main_frame, text="Sélectionner dossier", command=self.select_directory).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(main_frame, textvariable=self.selected_dir).grid(row=0, column=1, sticky=tk.W)
        
        # Zone de requête utilisateur
        query_frame = ttk.LabelFrame(main_frame, text="Requête Utilisateur", padding="5")
        query_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        ttk.Label(query_frame, text="Posez votre question ou décrivez le besoin:").grid(row=0, column=0, sticky=tk.W)
        
        self.query_text = ScrolledText(query_frame, height=4, width=80)
        self.query_text.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Un seul bouton d'action
        ttk.Button(main_frame, text="Analyser", command=self.process_all).grid(row=2, column=0, columnspan=2, pady=10)
        
        # Progression
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.progress_label = ttk.Label(progress_frame, text="")
        self.progress_label.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Zone de texte pour le résultat
        self.result_text = ScrolledText(main_frame, height=20, width=100)
        self.result_text.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configuration du redimensionnement
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

    def update_progress(self, current, total, message=""):
        """Met à jour la barre de progression et le message"""
        progress = (current / total) * 100 if total > 0 else 0
        self.progress_var.set(progress)
        self.progress_label.config(text=f"{message} ({current}/{total})")
        self.root.update_idletasks()

    def select_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.selected_dir.set(directory)

    def process_all(self):
        """Exécute toutes les étapes d'analyse en séquence"""
        if not self.selected_dir.get():
            messagebox.showwarning("Attention", "Veuillez d'abord sélectionner un dossier.")
            return
        
        query = self.query_text.get("1.0", tk.END).strip()
        if not query:
            messagebox.showwarning("Attention", "Veuillez saisir une requête.")
            return
        
        try:
            # 1. Indexation
            self.index_project()
            
            # 2. Clarification de la requête
            self.update_progress(0, 4, "Clarification de la requête...")
            clarified = self.clarify_query(query)
            
            # 3. Filtrage
            self.update_progress(1, 4, "Filtrage des fichiers pertinents...")
            self.filter_relevant_files(query)
            
            # 4. Génération du résultat final
            self.update_progress(2, 4, "Génération du rapport...")
            self.generate_enhanced_markdown(clarified)
            
            self.update_progress(4, 4, "Analyse terminée!")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue: {str(e)}")

    def clarify_query(self, query):
        """Clarifie et enrichit la requête utilisateur"""
        system_prompt = """You are an expert code analyst. Your task is to:
        1. Analyze the user's query about code analysis
        2. Clarify and expand the query to be more specific
        3. Add relevant technical aspects that might have been implied
        4. Format the response as:
            {
                "clarified_query": "The expanded and clarified version of the query",
                "analysis_points": ["specific point 1", "specific point 2", ...],
                "technical_focus": ["technical aspect 1", "technical aspect 2", ...]
            }
        """
        
        try:
            chat_response = self.client.chat.completions.create(
                model="Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {query}"},
                ],
                temperature=0.3,
                max_tokens=512
            )
            return json.loads(chat_response.choices[0].message.content)
        except Exception as e:
            return {
                "clarified_query": query,
                "analysis_points": ["Error in query clarification"],
                "technical_focus": []
            }

    def list_python_files(self, directory):
        py_files = []
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', 'env', '__pycache__']]
            for file in files:
                if file.endswith('.py') and not self.should_skip_file(file):
                    filepath = os.path.join(root, file)
                    relative_path = os.path.relpath(filepath, directory)
                    py_files.append((relative_path, filepath))
        return py_files

    def should_skip_file(self, filename):
        skip_patterns = [
            r'__init__\.py$',
            r'test_.*\.py$',
            r'.*_test\.py$',
            r'setup\.py$',
            r'.*_pb2\.py$'
        ]
        return any(re.match(pattern, filename) for pattern in skip_patterns)

    def index_project(self):
        directory = self.selected_dir.get()
        py_files = self.list_python_files(directory)
        total_files = len(py_files)
        
        self.project_index.clear()
        self.update_progress(0, total_files, "Indexation en cours...")

        for i, (rel_path, abs_path) in enumerate(py_files, start=1):
            content = self.read_file(abs_path)
            imports = self.extract_imports(content)
            functions = self.extract_function_signatures(content)
            summary = self.generate_file_summary(content)
            
            self.project_index[rel_path] = {
                "imports": imports,
                "functions": functions,
                "summary": summary,
                "full_content": content
            }
            self.update_progress(i, total_files, f"Indexation: {rel_path}")

    def read_file(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    def extract_imports(self, content):
        imports = re.findall(r'^(?:from|import).*$', content, re.MULTILINE)
        return imports

    def extract_function_signatures(self, content):
        pattern = r'^(def|class)\s+([^\(:]+).*?:'
        matches = re.finditer(pattern, content, re.MULTILINE)
        functions = []
        for m in matches:
            func_type = m.group(1)
            name = m.group(2)
            functions.append({"type": func_type, "name": name})
        return functions

    def generate_file_summary(self, content):
        system_prompt = """You are a technical documentation expert. 
        Given the following Python code, provide a short 1-2 line summary of what this file does overall. 
        No code details, just a high-level summary."""
        try:
            chat_response = self.client.chat.completions.create(
                model="Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
                temperature=0.3,
                max_tokens=128
            )
            return chat_response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating summary: {str(e)}"

    def filter_relevant_files(self, query):
        files_info = ""
        for f, info in self.project_index.items():
            files_info += f"\nFILE: {f}\nSummary: {info['summary']}\nFunctions: {[func['name'] for func in info['functions']]}\n"

        system_prompt = """You are a technical documentation expert. Identify which files and functions are most relevant to the user's query.
        Return your answer in JSON format:
        {
            "files": [
                {
                    "file": "filename.py",
                    "functions": [
                        {"name": "func_name", "include": "full" or "summary"}
                    ]
                }
            ]
        }"""

        try:
            chat_response = self.client.chat.completions.create(
                model="Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {query}\nFiles:\n{files_info}"},
                ],
                temperature=0.3,
                max_tokens=1024
            )
            response_text = chat_response.choices[0].message.content.strip()
            
            if response_text.startswith("```") and response_text.endswith("```"):
                lines = response_text.split("\n")
                lines = lines[1:-1]
                response_text = "\n".join(lines).strip()

            self.relevant_selection = json.loads(response_text)
            
        except Exception as e:
            self.relevant_selection = {"files": []}
            print(f"Error in filtering: {e}")

    def get_function_code(self, file_content, func_name):
        pattern = rf'^(def|class)\s+{func_name}\s*\(.*?\):((?:\n\s+.*)*)'
        match = re.search(pattern, file_content, re.MULTILINE)
        if match:
            return "def " + func_name + match.group(2)
        pattern_alt = rf'^(def|class)\s+{func_name}[^:]*:((?:\n\s+.*)*)'
        match_alt = re.search(pattern_alt, file_content, re.MULTILINE)
        if match_alt:
            return "def " + func_name + match_alt.group(2)
        return f"# Function {func_name} not found in the file."

    def generate_enhanced_markdown(self, clarified_query):
        """Génère le markdown final avec la requête clarifiée et le code"""
        output = "# Analyse de Code\n\n"
        
        # Section requête
        output += "## Requête d'Analyse\n\n"
        output += f"### Requête Originale\n{self.query_text.get('1.0', tk.END).strip()}\n\n"
        output += f"### Requête Clarifiée\n{clarified_query['clarified_query']}\n\n"
        
        # Points d'analyse
        output += "### Points d'Analyse\n"
        for point in clarified_query['analysis_points']:
            output += f"- {point}\n"
        output += "\n"
        
        # Focus technique
        output += "### Focus Technique\n"
        for focus in clarified_query['technical_focus']:
            output += f"- {focus}\n"
        output += "\n"
        
        # Code pertinent
        output += "## Code Pertinent\n\n"
        
        for item in self.relevant_selection.get("files", []):
            file = item["file"]
            if file not in self.project_index:
                continue

            info = self.project_index[file]
            output += f"### {file}\n\n"
            
            if not item["functions"]:
                output += f"```python\n# File summary: {info['summary']}\n```\n\n"
                continue

            for func_info in item["functions"]:
                func_name = func_info["name"]
                include = func_info.get("include", "summary")
                func_code = self.get_function_code(info["full_content"], func_name)
                
                if include == "full":
                    output += f"```python\n{func_code}\n```\n\n"
                else:
                    summary = self.generate_function_description(func_code)
                    output += f"```python\n# {summary}\n# Function: {func_name}\n```\n\n"

        # Sauvegarde et affichage
        with open('codeBase.md', 'w', encoding='utf-8') as f:
            f.write(output)
        
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, output)
        
        messagebox.showinfo("Succès", "Analyse terminée! Le fichier codeBase.md a été généré.")

    def generate_function_description(self, code_content):
        system_prompt = """You are a technical documentation expert. Analyze the Python code and provide a concise description including:
        1. A brief summary (1-2 lines)
        2. Input parameters
        3. Output/return value"""

        try:
            chat_response = self.client.chat.completions.create(
                model="Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Code:\n{code_content}"},
                ],
                temperature=0.3,
                max_tokens=256
            )
            return chat_response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating description: {str(e)}"

def main():
    root = tk.Tk()
    app = CodeBaseGenerator(root)
    root.mainloop()

if __name__ == '__main__':
    main()