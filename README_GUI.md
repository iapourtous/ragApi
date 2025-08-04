# Book Manager GUI - Utilitaire Graphique

Utilitaire graphique tkinter pour ajouter facilement des livres à l'API RAG via une interface intuitive.

## 🚀 Fonctionnalités

### Upload et Traitement
- **Sélection de fichier PDF** avec validation automatique
- **Téléversement d'image de couverture** (optionnel)
- **Configuration des options de traitement** (illustrations, pages début/fin)
- **Prévisualisation PDF** de la première page

### Métadonnées
- **Titre et auteur** (requis)
- **Description** avec génération automatique via l'API
- **Catégorie et sous-catégorie** avec valeurs prédéfinies
- **Édition** et options de visibilité publique

### Interface Utilisateur
- **Interface moderne** avec widgets ttk
- **Validation en temps réel** des champs
- **Barre de progression** pour les opérations longues
- **Messages de statut** informatifs
- **Prévisualisations** des images et PDFs

## 📋 Prérequis

### Serveur API
L'API RAG doit être en cours d'exécution sur `http://localhost:8081`

```bash
cd /home/dess4ever/workspace/ragApi/app
python run.py
```

### Dépendances Python
```bash
pip install Pillow requests
```

## 🎯 Utilisation

### Lancement
```bash
cd /home/dess4ever/workspace/ragApi/app
python book_manager_gui.py
```

### Processus d'Ajout de Livre

1. **Sélectionner le PDF**
   - Cliquer sur "Sélectionner PDF"
   - Choisir votre fichier PDF
   - Le titre sera auto-rempli basé sur le nom du fichier

2. **Remplir les Métadonnées**
   - **Titre*** et **Auteur*** (obligatoires)
   - Édition, catégorie, sous-catégorie
   - Description (ou utiliser "Générer auto")

3. **Configurer le Traitement**
   - Cocher "Traiter les illustrations" si nécessaire
   - Spécifier les pages début/fin (0 = tout le document)
   - Marquer comme public si désiré

4. **Image de Couverture** (optionnel)
   - Sélectionner une image
   - Prévisualisation automatique

5. **Prévisualisation PDF** (optionnel)
   - Cliquer sur "Générer prévisualisation"
   - Voir la première page du document

6. **Validation et Création**
   - Cliquer sur "Valider et créer"
   - Suivre la progression via la barre de statut
   - Le traitement PDF se fait en arrière-plan

## ⚙️ Configuration API

L'utilitaire communique avec l'API via les endpoints suivants :

- `POST /book/` - Création de livre
- `POST /pdf/generate-preview` - Prévisualisation PDF  
- `POST /book/generate_description` - Génération automatique de description

### Modifier l'URL de l'API
Dans `book_manager_gui.py`, ligne 34 :
```python
self.api_base_url = "http://localhost:8081"  # Modifier si nécessaire
```

## 🗂️ Catégories Prédéfinies

- Fiction
- Philosophie  
- Programmation
- Religion
- Psychologie
- Economie
- Administratif
- Restauration

## 🔧 Fonctionnalités Avancées

### Génération Automatique de Description
- Utilise l'API pour analyser le contenu du PDF
- Génère une description engageante basée sur le contenu
- Temps de traitement : 30-60 secondes selon la taille

### Prévisualisation PDF
- Convertit la première page en image WebP
- Redimensionnement automatique pour l'affichage
- Cache temporaire nettoyé automatiquement

### Validation Robuste
- Vérification des champs obligatoires
- Validation des types de fichiers
- Contrôle de cohérence des pages début/fin
- Messages d'erreur explicites

## 🛠️ Développement

### Structure du Code
```
book_manager_gui.py
├── BookManagerGUI (classe principale)
├── Interface utilisateur (setup_ui)
├── Gestion des fichiers (select_pdf_file, select_cover_image)
├── Communication API (create_book, generate_description)
├── Validation (validate_form)
└── Utilitaires (clear_form, previews)
```

### Threading
- **Opérations longues** exécutées dans des threads séparés
- **Interface non-bloquante** pendant les appels API
- **Gestion d'erreurs** avec retour vers le thread principal

### Gestion d'Erreurs
- **Try-catch** sur toutes les opérations réseau
- **Messages utilisateur** clairs et informatifs
- **Rollback** automatique en cas d'échec
- **Logging** des erreurs pour le débogage

## 🔍 Dépannage

### L'API n'est pas accessible
- Vérifier que le serveur RAG est démarré sur le port 8081
- Contrôler les paramètres de firewall
- Modifier `api_base_url` si nécessaire

### Erreurs de dépendances
```bash
pip install --upgrade Pillow requests tkinter
```

### Problèmes de permissions
- Vérifier les droits de lecture sur les fichiers PDF
- S'assurer que le répertoire de destination est accessible en écriture

### Prévisualisations qui ne s'affichent pas
- Vérifier que l'API génère correctement les images
- Contrôler les permissions sur le répertoire `/images/`
- Redémarrer l'API si nécessaire

## 📝 Notes Techniques

- **Format d'images supportées** : JPG, PNG, GIF, BMP, WebP
- **Taille max recommandée** : PDF < 100MB, Images < 10MB  
- **Threading** : Opérations réseau asynchrones pour UX fluide
- **Mémoire** : Gestion automatique des ressources et cache temporaire