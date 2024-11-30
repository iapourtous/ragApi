import logging

from .file_utils import save_partial_data
from .text_utils import split_text_into_chunks
from .vector_utils import serialize_tensor
from flask import current_app
from app.models.ai_model import AIModel

ai_model = AIModel()

def filter_match_by_llm(match, query, api_key, model_type):
    """
    Utilise le LLM pour déterminer si un passage est pertinent pour la requête.
    
    Args:
        match: Dictionnaire contenant les informations du passage
        query: Requête utilisateur
        api_key: Clé API pour le modèle LLM
        model_type: Type de modèle LLM à utiliser
    
    Returns:
        bool: True si le passage est pertinent, False sinon
    """
    prompt = f"""En tant qu'expert en analyse de pertinence, évaluez si le passage suivant répond ou apporte du contexte pertinent à la question posée.
Répondez uniquement par 'OUI' ou 'NON'.

QUESTION:
{query}

PASSAGE (Page {match['page_num']}):
{match['text']}

Le passage répond-il à la question ou apporte-t-il un contexte pertinent ?
Réponse (OUI/NON):"""

    try:
        response = ai_model.generate_response(model_type, api_key, prompt)
        return response.strip().upper().startswith('OUI')
    except Exception as e:
        logging.error(f"Erreur lors de l'évaluation LLM de la pertinence: {e}")
        return True

def reduceTextForDescriptions(text, context, length=100):
    """
    Combine un résumé et des informations contextuelles pour générer une description concise.

    :param text: Résumé du contenu du livre.
    :param context: Informations contextuelles supplémentaires sur le livre.
    :param length: Nombre de mots cible pour la description.
    :return: Description générée par le modèle d'IA.
    """
    api_key = current_app.config['API_KEY']
    prompt = f"""
Rédigez une description concise d'un livre en combinant le résumé suivant et les informations contextuelles fournies. La description doit être d'environ {length} mots, informative et objective.

**Résumé du contenu du livre** :
{text}

**Informations contextuelles sur le livre** :
{context}

**Description** :
"""
    response = ai_model.generate_response(current_app.config['AI_MODEL_TYPE'], api_key, prompt)
    return response

def generate_ai_response(query, documentation, additional_instructions="", api_key=None, model_type=None):
    """
    Generates an AI response based on a user query and structured documentation.

    :param query: User's query.
    :param documentation: Structured documentation to base the response on.
    :param additional_instructions: Additional instructions for the AI model.
    :param api_key: API key for the AI model.
    :param model_type: Type of AI model to use.
    :return: AI-generated response.
    """
    if api_key is None or model_type is None:
        raise ValueError("api_key and model_type must be provided")

    prompt = f"""
Vous êtes un assistant expert en analyse documentaire, spécialisé dans l'extraction et la synthèse d'informations à partir de documents.

QUESTION :
{query}

DOCUMENTATION FOURNIE :
{documentation}

INSTRUCTIONS :
- Fournissez une réponse précise basée sur les documents fournis.
- Utilisez les résumés pour le contexte général.
- Assurez la précision, la cohérence et citez toujours vos sources.
- Format des citations :
  - Page unique : [Document: {{nom}}, Page {{numéro}}]
  - Plage de pages : [Document: {{nom}}, Pages {{début}}-{{fin}}]
- Structure de la réponse :
  - Synthèse globale.
  - Analyse détaillée avec points clés.
  - Conclusion.
  - Sources utilisées
  - Autres recherches associées.
  - Limite de l'analyze.
- Utilisez le Markdown pour la mise en forme avec titres, sous-titres et listes à puces.

{additional_instructions if additional_instructions else ""}

RÉPONSE :
"""

    try:
        response = ai_model.generate_response(
            model_type,
            api_key,
            prompt
        )

        if not response or not response.strip():
            return """# Erreur de Génération

## Problème Rencontré
La génération de la réponse n'a pas produit de contenu valide.

## Actions Suggérées
1. Veuillez réessayer votre requête.
2. Considérez reformuler votre question.
3. Vérifiez si la documentation fournie contient les informations nécessaires."""

        # Check for Markdown formatting
        if not any(marker in response for marker in ['#', '##', '-', '*']):
            response = f"""# Réponse à la Question

## Contenu Principal
{response}

## Sources
[Basé sur la documentation fournie]"""

        return response

    except Exception as e:
        error_message = f"""# Erreur Technique

## Description
Une erreur s'est produite lors du traitement de votre requête : {str(e)}

## Suggestions
1. Veuillez réessayer votre requête.
2. Si l'erreur persiste, contactez le support technique.

## État du Système
- Type de modèle : {model_type}
"""
        logging.error(f"Erreur lors de la génération de la réponse : {str(e)}")
        return error_message
    
def generate_combined_documentation(documents):
    documentation = """<?xml version="1.0" encoding="UTF-8"?>
<documentation>
    <query_context>
"""

    # Ajouter les correspondances
    for doc in documents:
        documentation += f"\t<document_matches filename='{doc['filename']}'>\n"
        
        # Trier les matches par page
        sorted_matches = sorted(doc['matches'], key=lambda x: get_page_number(x['page_range']))
        
        for match in sorted_matches:
            documentation += f"""\t\t<match>
            <score>{match['score']:.4f}</score>
            <page_range>{match['page_range']}</page_range>
            <content>{match['text']}</content>
        </match>\n"""
        documentation += "\t</document_matches>\n"

    documentation += "\t</query_context>\n\t<documents>\n"

    # Ajouter les métadonnées des documents
    for doc in documents:
        documentation += f"""\t\t<document>
            <metadata>
                <filename>{doc['filename']}</filename>
                <description>{doc['description']}</description>
            </metadata>
        </document>\n"""

    documentation += "\t</documents>\n</documentation>"

    return documentation

def get_page_number(page_range):
    """
    Extrait et calcule le numéro de page moyen à partir d'une chaîne de page_range.
    
    :param page_range: Chaîne de caractères représentant la plage de pages (ex: "Page 5" ou "Pages 3 à 7")
    :return: Numéro de page unique ou moyenne des pages
    """
    try:
        # Pour une page unique (ex: "Page 5")
        if page_range.startswith("Page "):
            return int(page_range.split(" ")[1])
        
        # Pour une plage de pages (ex: "Pages 3 à 7")
        elif page_range.startswith("Pages "):
            numbers = [int(num) for num in page_range.replace("Pages ", "").split(" à ")]
            return sum(numbers) / len(numbers)  # Retourne la moyenne
            
        return 0  # Valeur par défaut si le format n'est pas reconnu
        
    except Exception as e:
        logging.error(f"Erreur lors de l'extraction du numéro de page : {e}")
        return 0
    
def generate_overall_description(textes, model, existing_description=None, existing_descriptions=None,
                                   existing_descriptions_vectorized=None, partial_file=None, book=None):
    if existing_description and existing_descriptions and existing_descriptions_vectorized:
        logging.info("Description générale déjà existante, utilisation des données existantes")
        return existing_description, existing_descriptions, existing_descriptions_vectorized

    general_description = existing_descriptions or []
    descriptions_vectorized = existing_descriptions_vectorized or []

    # Niveau 0 : Les pages (feuilles)
    if not general_description:
        logging.info("Début de la génération de la description générale")
        # Créer le premier niveau avec les textes des pages et leurs numéros
        page_descriptions = []
        page_vectors = []
        for page in textes:
            page_info = {
                'text': page['text'],
                'page_range': f"Page {page['pageNumber']}",
                'start_page': page['pageNumber'],
                'end_page': page['pageNumber']
            }
            page_descriptions.append(page_info)

            embedding = model.encode(page['text'], convert_to_tensor=True, normalize_embeddings=True)
            page_vectors.append(serialize_tensor(embedding))

        general_description.append(page_descriptions)
        descriptions_vectorized.append(page_vectors)

        if partial_file and book:
            book.descriptions = general_description
            book.descriptions_vectorized = descriptions_vectorized
            save_partial_data(partial_file, book)
            logging.info("Premier niveau (pages) sauvegardé")

    current_level = general_description[-1]
    current_vectors = descriptions_vectorized[-1]

    while len(current_level) > 1:
        logging.info(f"Traitement du niveau avec {len(current_level)} éléments")
        next_level = []
        next_vectors = []
        i = 0

        while i < len(current_level):
            text1 = current_level[i]['text']
            start_page = current_level[i]['start_page']

            if i + 1 < len(current_level):
                text2 = current_level[i + 1]['text']
                end_page = current_level[i + 1]['end_page']
            else:
                text2 = None
                end_page = current_level[i]['end_page']

            # Créer une plage de pages précise
            if start_page == end_page:
                combined_range = f"Page {start_page}"
            else:
                combined_range = f"Pages {start_page} à {end_page}"

            previous_summary = next_level[-1]['text'] if next_level else None

            try:
                summary, embedding = generate_summary_from_texts(text1, text2, model, previous_summary)
                next_level.append({
                    'text': summary,
                    'page_range': combined_range,
                    'start_page': start_page,
                    'end_page': end_page
                })
                next_vectors.append(serialize_tensor(embedding))
            except Exception as e:
                logging.error(f"Erreur lors de la génération du résumé: {e}")
                if partial_file and book:
                    book.descriptions = general_description
                    book.descriptions_vectorized = descriptions_vectorized
                    save_partial_data(partial_file, book)
                raise

            i += 2

        general_description.append(next_level)
        descriptions_vectorized.append(next_vectors)

        if partial_file and book:
            book.descriptions = general_description
            book.descriptions_vectorized = descriptions_vectorized
            save_partial_data(partial_file, book)
            logging.info(f"Niveau {len(general_description)} sauvegardé")

        current_level = next_level
        current_vectors = next_vectors

    # Modifier le 'page_range' du dernier élément pour indiquer qu'il s'agit du résumé général
    if current_level and len(current_level) == 1:
        final_element = current_level[0]
        start_page = final_element['start_page']
        end_page = final_element['end_page']
        final_element['page_range'] = f"Résumé général du livre de la page {start_page} à la page {end_page}"

    final_description = current_level[0]['text'] if current_level else None

    if partial_file and book:
        book.description = final_description
        book.descriptions = general_description
        book.descriptions_vectorized = descriptions_vectorized
        save_partial_data(partial_file, book)
        logging.info("Description générale finale sauvegardée")

    return final_description, general_description, descriptions_vectorized

def generate_summary_from_texts(text1, text2, model, previous_summary=None):
    """
    Génère un résumé cohérent à partir de deux textes en tenant compte du contexte précédent.

    :param text1: Premier texte à résumer.
    :param text2: Deuxième texte à résumer (peut être None).
    :param model: Modèle de langage à utiliser pour la génération.
    :param previous_summary: Résumé précédent pour maintenir la cohérence (peut être None).
    :return: Tuple (résumé généré, embedding du résumé).
    """
    # Préparer le deuxième passage s'il existe
    if text2:
        passage2 = "[Passage 2]\n" + text2
    else:
        passage2 = ""

    if previous_summary:
        prompt = f"""Vous êtes un expert en synthèse documentaire. Votre tâche est de rédiger un résumé cohérent qui poursuit le résumé précédent en intégrant les nouvelles informations.

CONTEXTE PRÉCÉDENT :
{previous_summary}

TEXTES À RÉSUMER :
[Passage 1]
{text1}

{passage2}

Instructions :
- Maintenir la continuité avec le résumé précédent.
- Inclure les idées principales et les concepts clés.
- Assurer une structure logique et fluide.
- Limiter le résumé à maximum 500 mots.
- Utiliser un style clair et objectif.

RÉSUMÉ :"""
    else:
        prompt = f"""Vous êtes un expert en synthèse documentaire. Votre tâche est de rédiger un résumé cohérent et structuré des passages suivants.

TEXTES À RÉSUMER :
[Passage 1]
{text1}

{passage2}

Instructions :
- Identifier les thèmes principaux et les informations essentielles.
- Organiser les idées de manière logique.
- Limiter le résumé à maximum 500 mots.
- Utiliser un style clair et objectif.

RÉSUMÉ :"""

    # Générer le résumé en utilisant le modèle d'IA
    description = ai_model.generate_response(
        current_app.config['AI_MODEL_TYPE'],
        current_app.config['API_KEY'],
        prompt
    )

    # Générer l'embedding du résumé pour la vectorisation
    embedding = model.encode(description, convert_to_tensor=True, normalize_embeddings=True)
    # Enregistrer le résumé généré dans les logs pour suivi
    logging.info(description)
    return description, embedding

def merge_responses(responses, query, max_tokens=8000):
    """
    Fusionne les réponses partielles en plusieurs étapes si nécessaire.
    
    :param responses: Liste des réponses partielles
    :param query: Question originale
    :param max_tokens: Nombre maximum de tokens par lot
    :return: Réponse finale fusionnée
    """
    logging.info(f"Début de la fusion de {len(responses)} réponses")
    
    if len(responses) <= 1:
        return responses[0]

    api_key = current_app.config['API_KEY']
    intermediate_responses = []
    current_batch = []
    current_tokens = 0

    def merge_batch(batch):
        """Fusionne un lot de réponses."""
        batch_prompt = f"""En tant qu'expert en synthèse documentaire, fusionnez les réponses partielles suivantes en une réponse cohérente et complète.

QUESTION ORIGINALE :
{query}

RÉPONSES PARTIELLES À FUSIONNER :
{batch}

INSTRUCTIONS :
- Créez une synthèse unifiée et cohérente
- Évitez les répétitions
- Conservez toutes les informations pertinentes
- Gardez les citations importantes
- Utilisez le format Markdown avec titres et sous-titres
- Organisez la réponse de manière logique

RÉPONSE FUSIONNÉE :"""

        try:
            return ai_model.generate_response(
                current_app.config['AI_MODEL_TYPE_FOR_REPONSE'],
                api_key,
                batch_prompt
            )
        except Exception as e:
            logging.error(f"Erreur lors de la fusion d'un lot : {e}")
            return None

    # Première phase : fusion par lots
    for response in responses:
        estimated_tokens = estimate_tokens(response)
        
        if current_tokens + estimated_tokens > max_tokens:
            if current_batch:
                logging.info(f"Fusion d'un lot de {len(current_batch)} réponses")
                merged = merge_batch("\n\n---\n\n".join(current_batch))
                if merged:
                    intermediate_responses.append(merged)
                current_batch = [response]
                current_tokens = estimated_tokens
        else:
            current_batch.append(response)
            current_tokens += estimated_tokens

    # Traiter le dernier lot de la première phase
    if current_batch:
        logging.info(f"Fusion du dernier lot de {len(current_batch)} réponses")
        merged = merge_batch("\n\n---\n\n".join(current_batch))
        if merged:
            intermediate_responses.append(merged)

    logging.info(f"Première phase : {len(intermediate_responses)} réponses intermédiaires générées")

    # Deuxième phase : fusion récursive des réponses intermédiaires si nécessaire
    while len(intermediate_responses) > 1:
        new_intermediate_responses = []
        current_batch = []
        current_tokens = 0

        for response in intermediate_responses:
            estimated_tokens = estimate_tokens(response)
            
            if current_tokens + estimated_tokens > max_tokens:
                if current_batch:
                    logging.info(f"Fusion récursive d'un lot de {len(current_batch)} réponses")
                    merged = merge_batch("\n\n---\n\n".join(current_batch))
                    if merged:
                        new_intermediate_responses.append(merged)
                    current_batch = [response]
                    current_tokens = estimated_tokens
            else:
                current_batch.append(response)
                current_tokens += estimated_tokens

        # Traiter le dernier lot
        if current_batch:
            logging.info(f"Fusion récursive du dernier lot de {len(current_batch)} réponses")
            merged = merge_batch("\n\n---\n\n".join(current_batch))
            if merged:
                new_intermediate_responses.append(merged)

        intermediate_responses = new_intermediate_responses
        logging.info(f"Phase récursive : {len(intermediate_responses)} réponses intermédiaires restantes")

    final_response = intermediate_responses[0] if intermediate_responses else "Erreur lors de la fusion des réponses."
    logging.info("Fusion des réponses terminée")
    
    return final_response

def estimate_tokens(text):
    """
    Estime le nombre de tokens dans un texte.
    
    :param text: Texte à évaluer
    :return: Nombre estimé de tokens
    """
    # Estimation simple : ~1.3 tokens par mot
    return len(text.split()) * 1.3

def correct_ocr_text(page_text, app):
    """
    Corrige les erreurs OCR dans le texte d'une page.
    
    Args:
        page_text: Texte de la page à corriger
        app: Instance de l'application Flask
    Returns:
        Texte corrigé
    """
    prompt = f"""En tant qu'expert en correction de textes OCR, corrigez les erreurs potentielles dans le texte suivant 
tout en préservant son sens et sa structure. Retournez uniquement le texte corrigé, sans commentaires ni explications.

Texte à corriger:
{page_text}

Instructions:
- Corrigez les erreurs d'OCR courantes (caractères mal reconnus, mots fusionnés ou séparés incorrectement)
- Préservez la mise en page et la structure du texte
- Conservez la ponctuation d'origine sauf si manifestement erronée
- Ne modifiez pas le contenu sémantique
- Ne rajoutez pas de contenu
"""

    try:
        corrected_text = AIModel.generate_response(
            app.config['AI_MODEL_TYPE'],
            app.config['API_KEY'],
            prompt
        )
        logging.info(correct_ocr_text)
        return corrected_text
    except Exception as e:
        logging.error(f"Erreur lors de la correction OCR: {e}")
        return page_text