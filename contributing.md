# Guide de contribution

## Prérequis
- Python 3.8+
- MongoDB
- Accès aux API des modèles d'IA (OpenAI, Together, etc.)

## Installation de l'environnement de développement

1. Cloner le dépôt
```bash
git clone https://github.com/iapourtous/ragApi.git
cd ragApi
```

2. Créer et activer un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Sous Windows: venv\Scripts\activate
```

3. Installer les dépendances
```bash
pip install -r requirements.txt
```

4. Configurer les variables d'environnement (créer un fichier .env à la racine)
```
OPENAI_API_KEY=votre_clé_openai
MONGODB_URI=votre_uri_mongodb
```

## Structure du code
Voir le fichier `architecture.md` pour comprendre l'organisation du code.

## Conventions de codage
- Suivre la norme PEP 8 pour le formatage du code
- Utiliser des noms explicites pour les variables et fonctions
- Documenter les fonctions avec des docstrings
- Ajouter des commentaires pour le code complexe

## Processus de contribution

1. Créer une branche pour votre fonctionnalité
```bash
git checkout -b feature/nom-de-votre-fonctionnalite
```

2. Développer et tester votre code localement
```bash
python run.py
```

3. Exécuter les tests
```bash
pytest tests/
```

4. Soumettre une Pull Request avec une description détaillée de vos modifications

## Ajout d'un nouveau modèle d'IA

1. Créer une nouvelle classe dans `app/models/` qui hérite de `base_model.py`
2. Implémenter les méthodes requises (voir les autres modèles comme exemples)
3. Mettre à jour `model_loader.py` pour inclure votre nouveau modèle
4. Ajouter la configuration nécessaire dans `config.py`

## Ajout d'une nouvelle fonctionnalité

1. Identifier le composant approprié (modèle, service, route)
2. Ajouter le code nécessaire en suivant les conventions existantes
3. Créer des tests pour valider la fonctionnalité
4. Mettre à jour la documentation si nécessaire

## Résolution de problèmes courants

- **Erreurs MongoDB** : Vérifier la connexion et les permissions de la base de données
- **Problèmes d'API** : Vérifier les clés API et les quotas
- **Erreurs d'importation** : Vérifier la structure des imports et l'organisation des modules