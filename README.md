# **RAG API**  
**L'API au cœur d'un écosystème éthique et accessible d'intelligence artificielle**  

[![Visitez iapourtous.org](https://img.shields.io/badge/Visitez-iapourtous.org-blue)](https://iapourtous.org)

---

## 🌟 **Introduction**  
RAG API est le moteur derrière **[IA pour tous](https://iapourtous.org)**, une initiative dédiée à démocratiser l'accès à des outils IA avancés et éthiques. Grâce à cette API, **IA pour tous** permet d'explorer des documents libres comme jamais auparavant, en combinant une recherche augmentée, des résumés hiérarchiques, et des outils pédagogiques innovants.

Ce projet a pour ambition de transformer l'accès à la connaissance en mettant l'intelligence artificielle au service de tous, sans compromis sur la vie privée ou l'éthique.

---

## 🌟 **Ce que RAG API rend possible sur iapourtous.org**  
### 🔍 **Recherche Augmentée**  
- **Interroger une bibliothèque libre grâce à l'IA** :  
  Accédez directement aux passages pertinents dans une vaste bibliothèque de livres et documents libres.
- **Synthèses structurées** :  
  Obtenez des résumés hiérarchiques qui facilitent la compréhension des documents complexes.

### 🌳 **Apprentissage Alternatif et Exploration Interactive**  
- **Arbres de connaissances interactifs** :  
  Transformez un livre en une structure navigable, allant de l'essentiel aux détails.  
- **Quiz et questionnaires de compréhension** :  
  Enrichissez l'expérience de lecture avec des outils pédagogiques qui s'adaptent à votre progression.

### 📚 **Accessibilité et Inclusion**  
- **Accès universel** :  
  Offrir des outils IA accessibles à tous, sur des documents et livres libres, comme un **Wikisource augmenté par l'IA**.
- **Respect de la vie privée** :  
  Aucun suivi des utilisateurs et une gestion éthique des données.

---

## 🌟 **Pourquoi choisir RAG API ?**
1. **Démocratisation de l'IA** :  
   Mettre des outils avancés à disposition de tous, quel que soit le niveau technique ou les ressources.
2. **Éthique et Transparence** :  
   Respect de la vie privée, gestion responsable des données, et transparence dans les processus IA.  
3. **Éducation et Apprentissage** :  
   Une approche pédagogique qui facilite l'accès à la connaissance et encourage la curiosité.  
4. **Technologie Avancée** :  
   Exploitez des modèles de pointe et des algorithmes innovants pour une expérience utilisateur fluide et précise.

---

## 🔧 **Fonctionnalités Techniques**
### 🔒 **Sécurité et Gestion des Utilisateurs**
- Authentification JWT, protection reCAPTCHA, et gestion des rôles (admin/utilisateur).

### 📋 **Gestion des Documents**
- Importation et traitement de PDF sans limite de volume.
- Structuration automatique des contenus en arbres hiérarchiques.

### 🤖 **Recherche et Réponses Contextuelles**
- Recherche sémantique avancée et scoring intelligent des résultats.
- Génération de réponses enrichies avec citations précises.

### 📚 **Outils d'Apprentissage**
- Navigation interactive et visualisation des liens entre concepts.
- Suivi personnalisé de la progression.

---

## 🚀 **Installation et Utilisation Rapide**

### **Prérequis**  
- Python 3.8+  
- MongoDB  
- Clés API pour les services LLM  

### **Étapes d'installation**  

1. **Cloner le repository** :
   ```bash
   git clone https://github.com/iapourtous/ragApi.git
   cd rag-api
   ```

2. **Créer un environnement virtuel et installer les dépendances** :
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   pip install -r requirements.txt
   ```

3. **Configurer les variables d'environnement** dans un fichier `.env` :
   ```env
   API_KEY=your-api-key
   SECRET_KEY=your-secret-key
   RECAPTCHA_API_KEY=your-recaptcha-api-key
   ```

4. **Lancer MongoDB et l'application** :
   ```bash
   mongod
   python run.py
   ```

---

## 🎯 **Cas d'utilisation réels grâce à IA pour tous**
| Domaine        | Fonctionnalité principale              | Exemple d'utilisation                              |
|----------------|----------------------------------------|--------------------------------------------------|
| Éducation      | Résumés hiérarchiques et quiz          | Étudiants explorant des livres pédagogiques      |
| Recherche      | Recherche augmentée sur plusieurs PDF | Chercheurs analysant des articles scientifiques  |
| Droit          | Analyse de contrats et documents      | Avocats recherchant des clauses spécifiques      |

---

## 🤝 **Contribuer à RAG API et IA pour tous**
Nous avons besoin de votre aide pour rendre ce projet encore meilleur !  

1. **Participez à RAG API** :
   - Forkez le projet sur GitHub.
   - Proposez de nouvelles fonctionnalités ou améliorez les existantes.
   - Soumettez vos idées via une Pull Request.

2. **Partagez IA pour tous** :
   - Invitez votre entourage à utiliser [iapourtous.org](https://iapourtous.org).  
   - Rejoignez notre communauté et contribuez à démocratiser l'accès à l'IA.

---

## 📄 **Licence**
- **Licence AGPL-3.0** pour usage non commercial
- **Licence commerciale** pour usage professionnel

---

## 📨 **Contact**
Pour toute question ou suggestion, contactez-nous via [iapourtous.org](https://iapourtous.org).

---

