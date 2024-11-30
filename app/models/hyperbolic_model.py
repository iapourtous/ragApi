
from .base_model import BaseLLMModel
import openai 

class HyperbolicModel(BaseLLMModel):
    def initialize_client(self):
        openai.api_key = self.api_key
        openai.api_base = "https://api.hyperbolic.xyz/v1/"

    def generate_response(self, query, system="Tu es un assistant expert et pragmatique qui répond en Français et qui donne la réponse en fonction des documents fournis"):
        max_retries = 10  # Nombre maximal de tentatives
        retry_delay = 600  # Délai en secondes avant de réessayer*
        client = openai.OpenAI(
            api_key=self.api_key,
            base_url="https://api.hyperbolic.xyz/v1",
            )
        for attempt in range(max_retries):
            try:
                chat_completion = client.chat.completions.create(
                    model="Qwen/Qwen2.5-72B-Instruct",
                    messages=[
                        {"role": "system", "content": "Tu es un assistant expert en analyse documentaire"},
                        {"role": "user", "content": query}  # Assurez-vous que query est une chaîne
                    ],
                    temperature=0.2,
                    max_tokens=8192,
                )
                return chat_completion.choices[0].message.content

            except Exception as e:
                    print(f"Erreur rencontrée: {e}.")

