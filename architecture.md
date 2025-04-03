# Architecture de l'application RAG API

## Vue d'ensemble
Cette application est une API de Retrieval Augmented Generation (RAG) permettant de traiter et d'interroger des documents PDF en utilisant différents modèles d'IA.

## Composants principaux

### Modèles
- `base_model.py` : Définit la classe de base pour tous les modèles d'IA
- `ai_model.py` : Implémentation générique d'un modèle d'IA
- Implémentations spécifiques :
  - `openai_model.py` : Modèle utilisant l'API OpenAI
  - `together_model.py` : Modèle utilisant l'API Together
  - `qwen_model.py` : Modèle Qwen
  - `vllm_openai_model.py` : Modèle OpenAI via vLLM
  - `vision_model.py` : Modèle de vision pour traiter les images

### Base de données
- `mongoClient.py` : Client MongoDB pour la persistance des données
- Modèles de données :
  - `db_book.py` : Structure pour les livres/documents
  - `db_blog.py` : Structure pour les articles de blog
  - `db_contactMessage.py` : Structure pour les messages de contact
  - `user.py` : Structure pour les utilisateurs

### Traitement de PDF
- `pdf_aiEncode.py` : Encodage des documents PDF pour la recherche vectorielle
- `pdf_aiProcessing.py` : Traitement des PDF avec l'IA

### Services
- `sevice_manager.py` : Gestionnaire central des services
- Services spécifiques :
  - `user_service.py` : Gestion des utilisateurs
  - `book_service.py` : Gestion des documents
  - `blog_service.py` : Gestion des articles de blog
  - `contactMessageService.py` : Gestion des messages de contact
  - `queryData_service.py` : Gestion des requêtes

### Routes API
- `auth_routes.py` : Authentification
- `blog_routes.py` : Gestion de blog
- `book_routes.py` : Gestion des documents
- `contact_routes.py` : Gestion des contacts
- `pdf_routes.py` : Manipulation des PDF
- `question_routes.py` : Traitement des questions

### Utilitaires
- `ai_utils.py` : Fonctions d'aide pour l'IA
- `auth_utils.py` : Utilitaires d'authentification
- `cache_utils.py` : Gestion du cache
- `file_utils.py` : Manipulation de fichiers
- `images_utils.py` : Traitement d'images
- `pdfQuery_utils.py` : Requêtes sur les PDF
- `query_processor.py` : Traitement des requêtes
- `text_utils.py` : Manipulation de texte
- `vector_utils.py` : Gestion des vecteurs et embedding

## Flux de données
1. Téléchargement des PDF via les routes dédiées
2. Encodage et vectorisation des documents PDF
3. Stockage des informations dans MongoDB
4. Requêtes utilisateur traitées via les routes de question
5. Récupération des informations pertinentes via la recherche vectorielle
6. Génération de réponses contextualisées avec les modèles d'IA

## Architecture technique
- Backend : Python avec Flask (implicite d'après la structure)
- Base de données : MongoDB
- Modèles d'IA : OpenAI, Together, Qwen, etc.
- Vectorisation : Utilisation d'embeddings pour la recherche sémantique