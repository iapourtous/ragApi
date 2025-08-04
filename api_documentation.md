# Documentation API RAG - Version 3.0

## Vue d'ensemble

L'API RAG (Retrieval-Augmented Generation) est une application Flask simplifiée qui combine la recherche documentaire et la génération de texte par intelligence artificielle. Elle permet de gérer une bibliothèque de livres numériques et de poser des questions sur leur contenu en utilisant des modèles de langage avancés.

### Architecture

- **Backend** : Flask (Python)
- **Base de données** : MongoDB
- **Authentification** : Aucune (API ouverte)
- **IA** : Support de multiples modèles (OpenAI, Together, Groq, vLLM)
- **Traitement PDF** : Extraction et vectorisation automatique

### URL de base

```
http://localhost:8081
```

### Authentification

Cette API est maintenant **complètement ouverte** et ne nécessite aucune authentification. Tous les endpoints sont accessibles directement sans token ou identifiants.

---

## 📚 Gestion des livres

### POST /book/

Crée un nouveau livre.

**En-têtes requis :**
```
Content-Type: multipart/form-data
```

**Données du formulaire :**
```
title: "Le Capital"
author: "Karl Marx"
description: "Critique de l'économie politique"
public: true
category: "Economie"
subcategory: "Politique économique"
directory: "Economie"
begin: 0
end: 0
illustration: false
pdf_file: [fichier PDF]
cover_image: [fichier image optionnel]
```

**Réponse (201) :**
```json
{
  "_id": "507f1f77bcf86cd799439013",
  "title": "Le Capital",
  "author": "Karl Marx",
  "description": "Critique de l'économie politique",
  "public": true,
  "cover_image": "cover_20241219_120150.webp",
  "pdf_path": "Economie/Le_capital.pdf",
  "proprietary": "system",
  "category": "Economie",
  "subcategory": "Politique économique",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### GET /book/

Récupère la liste des livres accessibles à l'utilisateur.

**Paramètres de requête :**
- `page` (int, optionnel) : Page (défaut: 1)
- `per_page` (int, optionnel) : Éléments par page (défaut: 10)

**Réponse (200) :**
```json
{
  "books": [
    {
      "_id": "507f1f77bcf86cd799439013",
      "title": "Le Capital",
      "author": "Karl Marx",
      "description": "Critique de l'économie politique",
      "public": true,
      "cover_image": "cover_20241219_120150.webp",
      "pdf_path": "Economie/Le_capital.pdf",
      "proprietary": "system",
      "category": "Economie",
      "subcategory": "Politique économique"
    }
  ],
  "total": 25,
  "page": 1,
  "perPage": 10
}
```

### GET /book/{book_id}

Récupère les détails d'un livre spécifique.

**Réponse (200) :**
```json
{
  "_id": "507f1f77bcf86cd799439013",
  "title": "Le Capital",
  "author": "Karl Marx",
  "description": "Critique de l'économie politique",
  "public": true,
  "cover_image": "cover_20241219_120150.webp",
  "pdf_path": "Economie/Le_capital.pdf",
  "proprietary": "system",
  "category": "Economie",
  "subcategory": "Politique économique",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Codes d'erreur :**
- `404` : Livre non trouvé

### PUT /book/{book_id}

Met à jour un livre existant.

**Données du formulaire :**
```
title: "Le Capital - Édition révisée"
description: "Nouvelle description"
public: false
cover_image: [nouveau fichier image optionnel]
```

**Réponse (200) :**
```json
{
  "_id": "507f1f77bcf86cd799439013",
  "title": "Le Capital - Édition révisée",
  "author": "Karl Marx",
  "description": "Nouvelle description",
  "public": false,
  "updated_at": "2024-01-15T11:00:00Z"
}
```

### DELETE /book/{book_id}

Supprime un livre.

**Réponse (200) :**
```json
{
  "message": "Book deleted"
}
```

### POST /book/generate-cover

Génère une image de couverture à partir de la première page du PDF.

**Corps de la requête :**
```json
{
  "filename": "Economie/Le_capital.pdf"
}
```

**Réponse (200) :**
```json
{
  "message": "Cover image generated successfully",
  "cover_image": "cover_20241219_120150.webp",
  "book": {
    "_id": "507f1f77bcf86cd799439013",
    "title": "Le Capital",
    "cover_image": "cover_20241219_120150.webp"
  }
}
```

### POST /book/generate_description

Génère une description automatique pour un livre.

**Corps de la requête :**
```json
{
  "pdf_files": ["Economie/Le_capital.pdf"],
  "context": "Livre d'économie politique du 19ème siècle"
}
```

**Réponse (200) :**
```json
{
  "description": "Le Capital est une œuvre majeure de Karl Marx qui analyse le système capitaliste...",
  "book": {
    "_id": "507f1f77bcf86cd799439013",
    "title": "Le Capital",
    "description": "Le Capital est une œuvre majeure de Karl Marx..."
  }
}
```

### GET /book/title/{title}/descriptions

Récupère les descriptions d'un livre par son titre.

**Réponse (200) :**
```json
{
  "descriptions": [
    [
      {
        "text": "Introduction au Capital...",
        "page": 1
      }
    ]
  ]
}
```

### POST /book/title/{title}/similarity

Calcule la similarité entre une requête et les descriptions d'un livre.

**Corps de la requête :**
```json
{
  "query": "Qu'est-ce que la plus-value ?"
}
```

**Réponse (200) :**
```json
{
  "similarities": [
    {
      "level": 0,
      "index": 5,
      "score": 0.89,
      "text": "La plus-value est la différence entre..."
    }
  ]
}
```

---

## 🔍 Recherche vectorielle de livres

### POST /book/search

**[NOUVEAU]** Recherche sémantique de livres basée sur leur description avec des embeddings pré-calculés.

**Corps de la requête :**
```json
{
  "query": "philosophie médiévale thomiste et scolastique",
  "k": 5,
  "threshold": 0.6,
  "category": "Religion",
  "author": "Thomas"
}
```

**Paramètres :**
- `query` (string, requis) : Requête de recherche sémantique
- `k` (int, optionnel) : Nombre maximum de résultats (défaut: 5, max: 50)
- `threshold` (float, optionnel) : Seuil de similarité minimum 0-1 (défaut: 0.5)
- `category` (string, optionnel) : Filtrer par catégorie
- `author` (string, optionnel) : Filtrer par auteur (recherche partielle)

**Réponse (200) :**
```json
{
  "query": "philosophie médiévale thomiste",
  "total_found": 2,
  "returned_count": 2,
  "execution_time": 0.045,
  "results": [
    {
      "book": {
        "_id": "6739f7282ff1a56cbac0b138",
        "title": "La somme théologique",
        "author": "Thomas d'Aquin",
        "description": "La Somme théologique de Thomas d'Aquin est une œuvre majeure...",
        "category": "Religion",
        "subcategory": "Théologie",
        "cover_image": "cover_20241130_154600.webp"
      },
      "similarity_score": 0.89
    },
    {
      "book": {
        "_id": "67348e76207687815b7610ba",
        "title": "Catéchisme de l'église Catholique",
        "author": "",
        "description": "Le Catéchisme de l'Église catholique (CEC) est un ouvrage majeur...",
        "category": "Religion",
        "subcategory": "Catéchisme",
        "cover_image": "cover_20241130_154557.webp"
      },
      "similarity_score": 0.72
    }
  ]
}
```

**Codes d'erreur :**
- `400` : Requête JSON manquante ou query vide
- `500` : Erreur lors de la recherche

**Exemples de requêtes :**
```bash
# Recherche simple
curl -X POST http://localhost:8081/book/search \
  -H "Content-Type: application/json" \
  -d '{"query": "économie politique marxiste"}'

# Recherche avec filtres
curl -X POST http://localhost:8081/book/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "analyse théologique",
    "k": 3,
    "threshold": 0.7,
    "category": "Religion"
  }'
```

### GET /book/embeddings/stats

Récupère les statistiques des embeddings de descriptions de livres.

**Réponse (200) :**
```json
{
  "total_books": 27,
  "books_with_embeddings": 25,
  "books_with_descriptions": 26,
  "books_needing_embeddings": 1,
  "embedding_coverage": 96.15
}
```

### POST /book/embeddings/migrate

Lance la migration des embeddings pour les livres qui en ont besoin.

**Corps de la requête :**
```json
{
  "batch_size": 10
}
```

**Réponse (200) :**
```json
{
  "total_books": 5,
  "processed": 5,
  "errors": 0,
  "success_rate": 100.0
}
```

---

## ❓ Système de questions (RAG)

### 🔄 GET /pdf/process-sse

**[RECOMMANDÉ]** Traite une requête sur un ou plusieurs livres avec réponse en streaming temps réel. Cet endpoint supporte le mode infinite et la sélection multi-livres.

**Paramètres de requête :**
- `query` (string, requis) : Question à poser
- `files` (array, requis) : Liste des chemins PDF (paramètre multiple pour multi-livres)
- `max_page` (int, optionnel) : Limite de pages à analyser (défaut: 30)
- `new` (string, optionnel) : "new" pour bypasser le cache
- `additional_instructions` (string, optionnel) : Instructions contextuelles supplémentaires

**Fonctionnalités avancées :**
- ✅ **Multi-livres** : Analyse simultanée de plusieurs sources
- ✅ **Streaming SSE** : Progression en temps réel
- ✅ **Mode infinite** : Décomposition automatique en sous-questions
- ✅ **NER intelligent** : Reconnaissance d'entités nommées avec spaCy
- ✅ **Cache optimisé** : Évite les retraitements inutiles
- ✅ **Groq + Kimi K2-Instruct** : IA de dernière génération

**Exemple livre unique :**
```bash
curl "http://localhost:8081/pdf/process-sse?query=Qui%20est%20Dieu%20?&files=Religion/bible.pdf&max_page=10"
```

**Exemple multi-livres :**
```bash
curl "http://localhost:8081/pdf/process-sse?query=Qu%20est-ce%20que%20la%20sagesse%20?&files=Religion/bible.pdf&files=Philosophie/Discours_de_la_méthode.pdf&files=Religion/Catechisme_Eglise_Catholique.pdf&max_page=20&additional_instructions=Je%20veux%20une%20analyse%20comparative"
```

**Réponse SSE (streaming) :**
```
data: Démarrage du traitement...

data: Clarification de la question

data: Extraction des entités nommées...

data: Vectorisation de la requête...

data: Vérification du cache...

data: Chargement du fichier Religion/bible.pdf...

data: Filtrage par LLM des passages retenus...

data: Filtrage LLM: 50.0% complété...

data: Filtrage LLM: 100.0% complété...

data: Génération de la réponse par lot...

data: Réception de la réponse partielle 1/1...

data: Sauvegarde de la réponse dans la base de données...

data: Traitement terminé.

data: {"LLMresponse": "# Introduction : Présentation de la Bible Segond...", "documents": [], "matches": {"all_matches": [...]}, "_id": "..."}
```

**Format de la réponse finale :**
```json
{
  "LLMresponse": "Réponse structurée en markdown avec références intégrées",
  "documents": [],
  "matches": {
    "all_matches": [
      {
        "text": "Extrait du document source...",
        "score": 0.92,
        "page_range": "Page 584",
        "file": "Religion/bible.pdf",
        "page_num": 584
      }
    ]
  },
  "_id": "identifiant_unique_reponse"
}
```

**Codes d'erreur :**
- `400` : Paramètres manquants (query ou files)
- `404` : Fichier PDF non trouvé
- `500` : Erreur de traitement IA

**Notes techniques :**
- **Content-Type** : `text/event-stream` (Server-Sent Events)
- **Timeout recommandé** : 120 secondes minimum
- **Limite multi-livres** : 7 livres maximum recommandé
- **Modèles IA** : Utilise la configuration `AI_MODEL_TYPE` et `AI_MODEL_TYPE_FOR_RESPONSE`

---

### POST /question/ask

**[LEGACY]** Pose une question sur le contenu d'un seul livre. Préférer `/pdf/process-sse` pour les nouvelles intégrations.

**Corps de la requête :**
```json
{
  "question": "Qu'est-ce que la plus-value selon Marx ?",
  "bookId": "507f1f77bcf86cd799439013",
  "context": "Dans le contexte économique",
  "isInfinite": false,
  "temperature": 0.7,
  "model": "qwen-max"
}
```

**Réponse (200) :**
```json
{
  "answer": "Selon Marx, la plus-value est la différence entre la valeur créée par le travailleur et le salaire qu'il reçoit. C'est le fondement de l'exploitation capitaliste...",
  "references": [
    {
      "page": 127,
      "score": 0.92,
      "text": "La plus-value est la différence entre la valeur que le travailleur ajoute au produit..."
    }
  ],
  "processingTime": 2.34,
  "queryTime": 1.89,
  "modelUsed": "qwen-max"
}
```

**Codes d'erreur :**
- `400` : Question ou ID de livre manquant
- `404` : Livre non trouvé ou aucun passage pertinent
- `500` : Erreur lors de la génération de la réponse

### POST /question/generate-questions

Génère des questions sur un sujet spécifique basées sur le contenu d'un livre.

**Corps de la requête :**
```json
{
  "title": "Le Capital",
  "pages": [
    {"level": 0, "index": 5},
    {"level": 1, "index": 12}
  ],
  "subject": "La plus-value"
}
```

**Réponse (200) :**
```json
{
  "questions": "1. Comment Marx définit-il la plus-value ?\n2. Quelle est la différence entre plus-value absolue et relative ?\n3. Comment la plus-value est-elle extraite du travail ouvrier ?"
}
```

---

## ⚙️ Configuration

### Variables d'environnement requises

```bash
# Configuration de base (optionnel)
SECRET_KEY=your_secret_key_here

# Chemins de stockage
PDF_FOLDER=pdf
IMAGE_FOLDER=images
FOLDER_PATH=db
MODEL_PATH=model

# Configuration IA (RECOMMANDÉ: Groq pour performances optimales)
AI_MODEL_TYPE=groq
AI_MODEL_TYPE_FOR_RESPONSE=groq
DEVICE=cpu

# Clés API des modèles
OPENAI_API_KEY=your_openai_key
TOGETHER_API_KEY=your_together_key
MISTRAL_API_KEY=your_mistral_key
GROQ_API_KEY=your_groq_api_key

# Configuration des modèles
OPENAI_MODEL_NAME=o1-mini
TOGETHER_MODEL_NAME=meta-llama/Llama-3.1-70B-Instruct-Turbo
GROQ_MODEL_NAME=moonshotai/kimi-k2-instruct
VLLM_API_BASE=http://localhost:8000/v1
VLLM_MODEL_NAME=microsoft/Phi-3-mini-4k-instruct

# Fonctionnalités avancées
DISABLE_RECAPTCHA=true
```

### Modèles IA supportés

1. **Groq** : Modèles ultra-rapides (moonshotai/kimi-k2-instruct) ⭐ **RECOMMANDÉ**
2. **OpenAI** : Modèles GPT (o1-mini par défaut)
3. **Together** : Modèles open-source (meta-llama/Llama-3.1-70B-Instruct-Turbo)
4. **vLLM** : Serveur local de modèles (localhost:8000, microsoft/Phi-3-mini-4k-instruct)
5. **Mistral** : Modèles Mistral AI

### Structure des dossiers

```
├── pdf/                    # Fichiers PDF stockés
│   ├── Economie/
│   ├── Philosophie/
│   └── ...
├── images/                 # Images de couverture
├── db/                     # Bases de données vectorielles
└── model/                  # Modèle d'embedding local
```

---

## 📋 Codes d'erreur communs

- `200` : Succès
- `201` : Créé avec succès
- `400` : Requête malformée ou données manquantes
- `401` : Non authentifié
- `403` : Accès refusé (rôle insuffisant ou reCAPTCHA)
- `404` : Ressource non trouvée
- `500` : Erreur serveur interne

---

## 🚀 Démarrage rapide

1. **Cloner et installer :**
```bash
git clone <repository>
cd ragApi/app
pip install -r requirements.txt
```

2. **Configurer l'environnement :**
```bash
cp .env.example .env
# Éditer .env avec vos clés API
```

3. **Lancer l'application :**
```bash
python run.py
```

4. **Tester l'API :**
```bash
curl -X GET http://localhost:8081/book/
```

---

## 📖 Exemples d'utilisation

### Workflow complet d'ajout d'un livre et de questions

1. **Ajouter un livre**
2. **Attendre le traitement automatique du PDF**
3. **Poser des questions sur le contenu**

### Exemple de session complète

```bash
# 1. Lister les livres disponibles
curl http://localhost:8081/book/

# 2. Poser une question sur un livre
curl -X POST http://localhost:8081/question/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qu est-ce que la plus-value ?",
    "bookId": "507f1f77bcf86cd799439013"
  }'

# 3. Ajouter un nouveau livre
curl -X POST http://localhost:8081/book/ \
  -F "title=Mon Nouveau Livre" \
  -F "author=Auteur Test" \
  -F "pdf_file=@/path/to/book.pdf"
```

---

## 🔧 Administration

### API ouverte
L'API est maintenant complètement ouverte et ne nécessite plus de comptes administrateur. Toutes les fonctionnalités sont accessibles directement :

### Fonctionnalités principales
- Gestion complète des livres (CRUD)
- Traitement des messages de contact
- Gestion des articles de blog
- Génération de couvertures et descriptions automatiques
- Système de questions RAG
- Traitement automatique des PDFs

---

Cette documentation couvre tous les endpoints principaux de l'API RAG. Pour des questions spécifiques ou des cas d'usage avancés, consultez le code source ou contactez l'équipe de développement.