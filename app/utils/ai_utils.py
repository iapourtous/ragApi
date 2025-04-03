import logging

from .file_utils import save_partial_data
from .vector_utils import serialize_tensor, vectorize_text
from flask import current_app, json
from app.models.ai_model import AIModel
from .model_utils import get_api_key_for_model

def filter_matches_by_llm_batch(passages_batch, query, api_key=None, model_type=None):
    """
    Évalue un lot de passages simultanément via LLM.
    
    Args:
        passages_batch: Liste des passages à évaluer
        query: Question utilisateur
        api_key: Clé API pour le modèle
        model_type: Type de modèle à utiliser
    """
    # Utiliser les valeurs par défaut du contexte Flask si disponibles
    if api_key is None:
        api_key = get_api_key_for_model(model_type)
    
    if model_type is None and current_app:
        model_type = current_app.config.get('AI_MODEL_TYPE', 'vllm_openai')
        
    passages_text = "\n\n".join([
        f"PASSAGE {i+1} (Page {match['page_num']}):\n{match['text']}"
        for i, match in enumerate(passages_batch)
    ])
    
    prompt = f"""En tant qu'expert en analyse de pertinence, évaluez si les passages suivants répondent ou apportent 
du contexte pertinent à la question posée. Pour chaque passage, répondez uniquement par OUI ou NON.

QUESTION:
{query}

{passages_text}

FORMAT DE RÉPONSE REQUIS:
Répondez exactement dans ce format, un résultat par ligne:
PASSAGE 1: OUI/NON
PASSAGE 2: OUI/NON
etc.

RÉPONSES:"""

    try:
        response = AIModel.generate_response(model_type, api_key, prompt)
        
        # Analyse des réponses
        results = []
        response_lines = response.strip().split('\n')
        for line in response_lines:
            if ':' in line:
                result = line.split(':')[1].strip().upper().startswith('OUI')
                results.append(result)
                
        # Si le nombre de réponses ne correspond pas au nombre de passages
        if len(results) != len(passages_batch):
            logging.warning(f"Nombre de réponses incorrect. Attendu: {len(passages_batch)}, Reçu: {len(results)}")
            return [True] * len(passages_batch)
            
        return results
        
    except Exception as e:
        logging.error(f"Erreur lors de l'évaluation batch LLM: {e}")
        return [True] * len(passages_batch)

def llm_filter_matches(initial_matches, query, api_key, model_type, send_progress=None):
    """
    Filtre les passages en évaluant plusieurs passages simultanément.
    """
    if send_progress:
        send_progress("Filtrage par LLM des passages retenus...")
    filtered_matches = []
    
    # Nombre de passages à évaluer par lot
    BATCH_SIZE = 5
    
    # Traitement par lots
    for i in range(0, len(initial_matches), BATCH_SIZE):
        batch = initial_matches[i:i + BATCH_SIZE]
        
        try:
            results = filter_matches_by_llm_batch(batch, query, api_key, model_type)
            
            # Ajouter les passages pertinents aux résultats filtrés
            for match, is_relevant in zip(batch, results):
                if is_relevant:
                    filtered_matches.append(match)
                    logging.info(f"Page {match['page_num']} conservée (score: {match['score']:.3f})")
                else:
                    logging.info(f"Page {match['page_num']} retirée (score: {match['score']:.3f})")
                    
            # Mise à jour du progrès
            if send_progress:
                progress = (i + len(batch)) / len(initial_matches) * 100
                send_progress(f"Filtrage LLM: {progress:.1f}% complété...")
            
        except Exception as e:
            logging.error(f"Erreur lors du traitement du lot {i//BATCH_SIZE + 1}: {e}")
            # En cas d'erreur, ajouter tous les passages du lot
            filtered_matches.extend(batch)

    # Tri final par numéro de page
    filtered_matches.sort(key=lambda x: x['page_num'])
    
    logging.info(f"Filtrage LLM terminé: {len(filtered_matches)}/{len(initial_matches)} passages retenus")
    return filtered_matches

def clarify_question(query, api_key, model_type):
    """
    Reformule la requête en une question claire et précise.
    
    Args:
        query: Requête utilisateur originale
        api_key: Clé API pour le modèle LLM
        model_type: Type de modèle LLM à utiliser
    
    Returns:
        str: Question clarifiée
    """
    prompt = f"""En tant qu'expert en analyse de questions, reformulez cette requête en une question claire, précise et bien structurée.

REQUÊTE ORIGINALE :
{query}

INSTRUCTIONS :
- Clarifier l'intention de la question
- Utiliser un langage précis et non ambigu
- Maintenir tous les éléments importants de la requête originale
- Structurer la question de manière logique
- Ne pas ajouter d'informations non présentes dans la requête originale

QUESTION CLARIFIÉE :"""

    try:
        clarified = AIModel.generate_response(model_type, api_key, prompt)
        logging.info(f"Question clarifiée: {clarified}")
        return clarified.strip()
    except Exception as e:
        logging.error(f"Erreur lors de la clarification de la question: {e}")
        return query

def reduceTextForDescriptions(text, context, length=100):
    """
    Combine un résumé et des informations contextuelles pour générer une description concise.

    :param text: Résumé du contenu du livre.
    :param context: Informations contextuelles supplémentaires sur le livre.
    :param length: Nombre de mots cible pour la description.
    :return: Description générée par le modèle d'IA.
    """
    # Utiliser la fonction centralisée de récupération de clés API
    model_type = current_app.config['AI_MODEL_TYPE']
    api_key = get_api_key_for_model(model_type)
    
    prompt = f"""
Rédigez une description concise d'un livre en combinant le résumé suivant et les informations contextuelles fournies. La description doit être d'environ {length} mots, informative et objective.

**Résumé du contenu du livre** :
{text}

**Informations contextuelles sur le livre** :
{context}

**Description** :
"""
    response = AIModel.generate_response(model_type, api_key, prompt)
    return response

def generate_ai_response(query, documentation, additional_instructions="", api_key=None, model_type=None):
    """
    Génère une réponse AI adaptée en fonction du type de question et des documents.
    """
    if api_key is None or model_type is None:
        raise ValueError("api_key and model_type must be provided")

    # Analyse du type de question et des documents
    analysis_prompt = f"""Analysez la question et la documentation fournie pour déterminer :
1. Le type de question (comparative, explicative, analytique, factuelle, historique, etc.)
2. Le type de documents fournis (techniques, historiques, légaux, religieux, etc.)
3. La structure de réponse la plus appropriée

QUESTION :
{query}

DOCUMENTATION FOURNIE :
{documentation}

INSTRUCTIONS ADDITIONNELLES :
{additional_instructions}

FORMAT DE RÉPONSE REQUIS (respectez strictement ce format) :
{{
    "question_type": "type_de_question",
    "document_types": ["type1", "type2"],
    "recommended_structure": [
        "section1",
        "section2"
    ]
}}"""

    try:
        # Analyse de la question et des documents
        structure_analysis = AIModel.generate_response(
            model_type,
            api_key,
            analysis_prompt,
            system="Vous êtes un expert en analyse documentaire et structuration de réponses."
        )
        
        # Extraction du JSON de la réponse
        json_str = structure_analysis
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
        
        # Nettoyage du JSON
        json_str = json_str.strip()
        
        # Parsing de l'analyse JSON
        try:
            analysis = json.loads(json_str)
        except json.JSONDecodeError as e:
            logging.error(f"Erreur de parsing JSON: {e}")
            logging.error(f"JSON string: {json_str}")
            analysis = {
                "question_type": "general",
                "document_types": ["unknown"],
                "recommended_structure": [
                    "Synthèse globale",
                    "Analyse détaillée",
                    "Conclusion"
                ]
            }

        # Validation des champs requis
        if not all(key in analysis for key in ["question_type", "document_types", "recommended_structure"]):
            raise ValueError("Structure JSON invalide")

        # Génération des instructions de structure spécifiques en utilisant generate_structure_instructions
        structure_instructions = generate_structure_instructions(
            analysis["question_type"],
            analysis["document_types"],
            analysis["recommended_structure"],
            additional_instructions
        )

        # Prompt principal pour la génération de la réponse
        main_prompt = f"""En tant qu'expert en analyse documentaire, générez une réponse structurée à la question suivante.

QUESTION :
{query}

DOCUMENTATION FOURNIE :
{documentation}

TYPE DE QUESTION : {analysis["question_type"]}
TYPES DE DOCUMENTS : {', '.join(analysis["document_types"])}

STRUCTURE REQUISE :
{structure_instructions}

INSTRUCTIONS ADDITIONNELLES :
{additional_instructions}

DIRECTIVES GÉNÉRALES :
- Utilisez le format Markdown pour la mise en forme
- Citez précisément les sources (format : [Document: X, Page Y])
- Restez objectif et précis
- Respectez strictement la structure fournie
- Adaptez le contenu de chaque section au contexte
- Utilisez des sous-sections si nécessaire
- Incluez des citations pertinentes des documents sources

RÉPONSE :"""

        # Génération de la réponse finale
        response = AIModel.generate_response(
            model_type,
            api_key,
            main_prompt,
            system=f"Vous êtes un expert en analyse documentaire, spécialisé dans les documents de type {', '.join(analysis['document_types'])}."
        )

        if not response or not response.strip():
            return generate_error_response("La génération n'a pas produit de contenu valide.")

        return response

    except Exception as e:
        logging.error(f"Erreur lors de la génération de la réponse : {str(e)}")
        return generate_error_response(str(e))

def generate_error_response(error_message):
    """
    Génère une réponse formatée en cas d'erreur.
    """
    return f"""# Erreur de Génération

## Problème Rencontré
{error_message}

## Actions Suggérées
1. Veuillez réessayer votre requête
2. Considérez reformuler votre question
3. Vérifiez si la documentation fournie contient les informations nécessaires

## État du Système
- Une erreur s'est produite lors du traitement
- Les données peuvent être incomplètes ou incorrectes"""

def generate_structure_instructions(question_type, document_types, recommended_structure, additional_instructions):
    """
    Génère des instructions de structure spécifiques selon le contexte en s'appuyant sur des formats académiques et professionnels.
    """
    structure_templates = {
        "comparative": """
# Introduction
- Présentation du contexte et des objectifs de la comparaison.

# Méthodologie Comparative
- Critères et méthodes d'analyse comparée.

# Analyse Comparative
- Examen détaillé des similitudes et des différences.

# Discussion
- Interprétation critique des résultats comparatifs.

# Conclusion
- Résumé des constatations et recommandations.

# Références
""",
        "explicative": """
# Introduction
- Contexte et présentation du sujet.

# Cadre Théorique
- Concepts, définitions et références théoriques.

# Analyse Explicative
- Développement détaillé des explications avec exemples.

# Discussion
- Implications, limites et perspectives.

# Conclusion
- Synthèse et recommandations.

# Références
""",
        "analytique": """
# Introduction
- Contexte, problématique et objectifs de l'analyse.

# Méthodologie
- Description des approches analytiques et outils utilisés.

# Analyse Approfondie
- Examen détaillé des données et des résultats.

# Discussion
- Interprétation critique et implications des analyses.

# Conclusion
- Résumé des analyses et recommandations.

# Références
""",
        "factuelle": """
# Introduction
- Contexte et objectifs de l'exposé factuel.

# Exposé des Faits
- Présentation chronologique et objective des faits.

# Analyse Contextuelle
- Mise en perspective et explication des faits.

# Conclusion
- Synthèse des faits et conclusions tirées.

# Références
""",
        "general": """
# Introduction
- Contexte général et définition de la problématique.

# Analyse et Synthèse
- Présentation détaillée des informations et analyse critique.

# Discussion
- Réflexions, implications et interprétations.

# Conclusion
- Résumé global et recommandations.

# Références
"""
    }

    # Sélection du template de base selon le type de question
    base_structure = structure_templates.get(question_type.lower(), structure_templates["general"])

    # Adaptation selon le type de document
    if "technical" in document_types:
        base_structure += """
# Annexes Techniques
- Spécifications, schémas et données techniques."""
    if "legal" in document_types:
        base_structure += """
# Cadre Légal
- Analyse des implications juridiques et réglementaires."""
    if "historical" in document_types:
        base_structure += """
# Contexte Historique
- Présentation du cadre temporel et analyse historique."""

    # Intégration des sections recommandées en évitant les répétitions
    # Les sections "Limites de l'analyse" et "Autres recherches associées" sont laissées à add_additional_sections
    for section in recommended_structure:
        section_norm = section.strip().lower()
        if section_norm not in base_structure.lower() and section_norm not in ["limites de l'analyse", "autres recherches associées"]:
            base_structure += f"\n# {section.strip()}"

    return base_structure
    
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

            # Utiliser la fonction commune pour la vectorisation
            embedding = vectorize_text(page['text'], model, chunk_content=False)
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
    model_type = current_app.config['AI_MODEL_TYPE']
    api_key = get_api_key_for_model(model_type)
        
    description = AIModel.generate_response(
        model_type,
        api_key,
        prompt
    )

    # Générer l'embedding du résumé en utilisant la fonction commune
    embedding = vectorize_text(description, model, chunk_content=False)
    # Enregistrer le résumé généré dans les logs pour suivi
    logging.info(description)
    return description, embedding

def merge_responses(app, responses, query, max_tokens=8000, additional_instructions="", send_progress=None, add_section=True):
    """
    Fusionne les réponses partielles en incluant les sections supplémentaires.
    """
    logging.info(f"Début de la fusion de {len(responses)} réponses")

    if send_progress:
        send_progress(f"Début de la fusion de {len(responses)} réponses partielles...")
    
    if len(responses) <= 1:
        response = responses[0]
        if send_progress:
            send_progress("Une seule réponse partielle détectée, pas de fusion nécessaire.")
        return add_additional_sections(response, query, app, additional_instructions, add_section)

    api_key = app['config']['API_KEY']
    intermediate_responses = []
    current_batch = []
    current_tokens = 0

    def merge_batch(batch, batch_count, total_batches):
        """Fusionne un lot de réponses."""
        if send_progress:
            send_progress(f"Fusion du lot {batch_count}/{total_batches} en cours...")
            
        batch_prompt = f"""En tant qu'expert en synthèse documentaire, fusionnez les réponses partielles suivantes en une réponse cohérente et complète.

QUESTION ORIGINALE :
{query}

RÉPONSES PARTIELLES À FUSIONNER :
{batch}

INSTRUCTIONS :
- Créez une synthèse unifiée et cohérente
- Évitez les répétitions
- Conservez toutes les informations pertinentes
- Gardez les citations importantes et les sources dans le format donné
- Utilisez le format Markdown avec titres et sous-titres
- Organisez la réponse de manière logique

RÉPONSE FUSIONNÉE :"""

        try:
            model_type = app['config']['AI_MODEL_TYPE_FOR_REPONSE']
            model_api_key = get_api_key_for_model(model_type, app['config'])
            
            # Si aucune clé n'est trouvée, utiliser celle fournie en argument
            if model_api_key is None:
                model_api_key = api_key
                
            merged = AIModel.generate_response(
                model_type,
                model_api_key,
                batch_prompt
            )
            if send_progress:
                send_progress(f"Lot {batch_count}/{total_batches} fusionné avec succès.")
            return merged
        except Exception as e:
            logging.error(f"Erreur lors de la fusion d'un lot : {e}")
            if send_progress:
                send_progress(f"Erreur lors de la fusion du lot {batch_count}/{total_batches}.")
            return None

    # Première phase : fusion par lots
    total_responses = len(responses)
    batch_count = 0
    for i, response in enumerate(responses, start=1):
        estimated_tokens = estimate_tokens(response)
        if current_tokens + estimated_tokens > max_tokens:
            # Fusion du batch précédent avant d'ajouter la réponse actuelle
            if current_batch:
                batch_count += 1
                merged = merge_batch("\n\n---\n\n".join(current_batch), batch_count, "?")
                if merged:
                    intermediate_responses.append(merged)
                current_batch = [response]
                current_tokens = estimated_tokens
            else:
                # Si la réponse seule dépasse le seuil, on tente de la fusionner directement.
                batch_count += 1
                merged = merge_batch(response, batch_count, "?")
                if merged:
                    intermediate_responses.append(merged)
                current_tokens = 0
                current_batch = []
        else:
            current_batch.append(response)
            current_tokens += estimated_tokens

    # Traiter le dernier lot de la première phase
    if current_batch:
        batch_count += 1
        merged = merge_batch("\n\n---\n\n".join(current_batch), batch_count, "?")
        if merged:
            intermediate_responses.append(merged)

    if send_progress:
        send_progress(f"Première phase terminée : {len(intermediate_responses)} réponses intermédiaires générées")

    # Deuxième phase : fusion récursive des réponses intermédiaires si nécessaire
    recursion_round = 1
    while len(intermediate_responses) > 1:
        if send_progress:
            send_progress(f"Début de la phase de fusion récursive {recursion_round} avec {len(intermediate_responses)} réponses intermédiaires...")
        
        new_intermediate_responses = []
        current_batch = []
        current_tokens = 0
        batch_count = 0
        total_batches = len(intermediate_responses)

        for i, response in enumerate(intermediate_responses, start=1):
            estimated_tokens = estimate_tokens(response)
            if current_tokens + estimated_tokens > max_tokens:
                if current_batch:
                    batch_count += 1
                    merged = merge_batch("\n\n---\n\n".join(current_batch), batch_count, total_batches)
                    if merged:
                        new_intermediate_responses.append(merged)
                    current_batch = [response]
                    current_tokens = estimated_tokens
                else:
                    # Même logique que précédemment si une seule réponse dépasse le seuil
                    batch_count += 1
                    merged = merge_batch(response, batch_count, total_batches)
                    if merged:
                        new_intermediate_responses.append(merged)
                    current_tokens = 0
                    current_batch = []
            else:
                current_batch.append(response)
                current_tokens += estimated_tokens

        # Traiter le dernier lot
        if current_batch:
            batch_count += 1
            merged = merge_batch("\n\n---\n\n".join(current_batch), batch_count, total_batches)
            if merged:
                new_intermediate_responses.append(merged)

        intermediate_responses = new_intermediate_responses
        if send_progress:
            send_progress(f"Fin de la phase récursive {recursion_round}, {len(intermediate_responses)} réponses restantes.")
        recursion_round += 1

    final_response = intermediate_responses[0] if intermediate_responses else "Erreur lors de la fusion des réponses."

    if send_progress:
        send_progress("Fusion des réponses intermédiaires terminée, ajout des sections supplémentaires...")

    final_response = add_additional_sections(final_response, query, app, additional_instructions, add_section)
    
    if send_progress:
        send_progress("Fusion terminée.")

    logging.info("Fusion des réponses terminée")
    return final_response

def add_additional_sections(response, query, app, additional_instructions="", add_section=True):
    """
    Ajoute les sections Limites de l'analyse et Autres recherches associées,
    en tenant compte des instructions supplémentaires.
    """
    if not add_section:
        return response

    prompt = f"""En tant qu'expert en analyse documentaire, examinez la réponse suivante et créez une version améliorée
qui intègre les instructions supplémentaires et ajoute deux sections importantes.

QUESTION ORIGINALE :
{query}

INSTRUCTIONS SUPPLÉMENTAIRES :
{additional_instructions}

RÉPONSE ACTUELLE :
{response}

INSTRUCTIONS POUR LA VERSION FINALE :
1. Intégrez les instructions supplémentaires dans la réponse principale
2. Assurez-vous que la réponse répond aux exigences spécifiques des instructions
3. Ajoutez une section "# Limites de l'analyse" qui identifie :
   - Les limitations potentielles de l'analyse
   - Les aspects non couverts par les documents
   - Les incertitudes ou zones grises
4. Ajoutez une section "# Autres recherches associées" qui suggère :
   - Des pistes de recherche complémentaires
   - Des aspects à approfondir
   - Des sources additionnelles potentielles
5. Utilisez le format Markdown
6. Restez concis et pertinent

RÉPONSE COMPLÈTE :"""

    try:
        model_type = app['config']['AI_MODEL_TYPE_FOR_REPONSE']
        model_api_key = get_api_key_for_model(model_type, app['config'])
            
        enhanced_response = AIModel.generate_response(
            model_type,
            model_api_key,
            prompt
        )
        return enhanced_response
    except Exception as e:
        logging.error(f"Erreur lors de l'ajout des sections supplémentaires : {e}")
        # En cas d'erreur, ajouter manuellement les sections
        return f"""{response}

# Limites de l'analyse
- Les informations fournies sont basées sur les documents disponibles
- Certains aspects peuvent nécessiter des sources supplémentaires
- L'analyse peut être limitée par la portée des documents fournis
- Les instructions supplémentaires peuvent ne pas être entièrement couvertes

# Autres recherches associées
- Consulter des sources complémentaires sur le sujet
- Explorer les développements récents
- Approfondir les aspects spécifiques mentionnés
- Rechercher des informations supplémentaires selon les instructions données"""

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
            get_api_key_for_model(app.config['AI_MODEL_TYPE'], app.config),
            prompt
        )
        logging.info(correct_ocr_text)
        return corrected_text
    except Exception as e:
        logging.error(f"Erreur lors de la correction OCR: {e}")
        return page_text