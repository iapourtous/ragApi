import os
import ast
import sys

class CodeExtractor:
    def extract_file_info(self, code):
        """Extrait les informations essentielles d'un fichier Python."""
        tree = ast.parse(code)
        return {
            'imports': self._get_imports(tree),
            'classes': self._get_classes(tree),
            'functions': self._get_functions(tree),
            'description': self._get_file_description(tree)
        }

    def _get_imports(self, tree):
        """Extrait les imports."""
        imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                imports.extend(n.name for n in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.extend(f"{node.module}.{n.name}" for n in node.names)
        return imports

    def _get_classes(self, tree):
        """Extrait les informations des classes."""
        classes = {}
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                methods = {}
                for n in node.body:
                    if isinstance(n, ast.FunctionDef):
                        methods[n.name] = ast.get_docstring(n) or "No documentation"
                
                classes[node.name] = {
                    'methods': methods,
                    'parent_classes': [base.id for base in node.bases if isinstance(base, ast.Name)],
                    'docstring': ast.get_docstring(node) or "No documentation"
                }
        return classes

    def _get_functions(self, tree):
        """Extrait les fonctions globales."""
        return [{'name': node.name, 
                'docstring': ast.get_docstring(node) or "No documentation"}
                for node in ast.iter_child_nodes(tree)
                if isinstance(node, ast.FunctionDef)]

    def _get_file_description(self, tree):
        """Extrait la description du module."""
        return ast.get_docstring(tree) or "No module description available."

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py [directory]")
        sys.exit(1)

    directory = sys.argv[1]
    extractor = CodeExtractor()
    project_summary = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                file_info = extractor.extract_file_info(code)
                relative_path = os.path.relpath(filepath, directory)
                
                summary = {
                    'file': relative_path,
                    'content': file_info
                }
                project_summary.append(summary)

    output = "=== Project Code Summary ===\n\n"
    for file_summary in project_summary:
        output += f"File: {file_summary['file']}\n"
        output += "-" * 50 + "\n"
        
        content = file_summary['content']
        output += f"Description: {content['description']}\n\n"
        
        if content['imports']:
            output += "Imports: " + ", ".join(content['imports']) + "\n\n"
        
        if content['classes']:
            output += "Classes:\n"
            for class_name, class_info in content['classes'].items():
                output += f"  - {class_name}"
                if class_info['parent_classes']:
                    output += f" (inherits from: {', '.join(class_info['parent_classes'])})"
                output += f"\n    Docstring: {class_info['docstring']}\n"
                if class_info['methods']:
                    output += "    Methods:\n"
                    for method_name, method_doc in class_info['methods'].items():
                        output += f"      - {method_name}\n        Docstring: {method_doc}\n"
        
        if content['functions']:
            output += "\nFunctions:\n"
            for func in content['functions']:
                output += f"  - {func['name']}\n    Docstring: {func['docstring']}\n"
        
        output += "\n"

    with open('code_summary.txt', 'w', encoding='utf-8') as f:
        f.write(output)

if __name__ == '__main__':
    main()