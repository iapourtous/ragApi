import logging
from mistralai import Mistral

from app.utils.images_utils import encode_image
from .base_model import BaseLLMModel


class PixtralModel(BaseLLMModel):
    def initialize_client(self):
        self.client = Mistral(api_key=self.api_key)

    def generate_response(self, image_path, query):
        # Encode image
        base64_image = encode_image(image_path)
        if not base64_image:
            return "Erreur lors de l'encodage de l'image."

        # Préparer les messages
        prompt = f"""Vous êtes un assistant expert en analyse d'images. Je te joins une image qui accompagne ce texte:
        {query}
        .Dis-moi ce qu'apporte cette image au texte. Pas de paraphrase, juste la réponse comme pour un modèle instruct."""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}
                ]
            }
        ]

        # Générer la réponse
        try:
            response = self.client.chat.complete(
                model=self.model_name,
                messages=messages
            )
            logging.info(f"Réponse générée par PixtralModel: {response.choices[0].message.content}")
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Erreur lors de la génération de la réponse: {e}")
            return f"Erreur lors de la génération de la réponse: {e}"