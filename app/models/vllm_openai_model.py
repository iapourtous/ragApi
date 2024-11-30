from .base_model import BaseLLMModel
import openai
from openai import OpenAI

class VLLMOpenAIModel(BaseLLMModel):
    def initialize_client(self, **kwargs):
        # Configuration spécifique pour vLLM
        self.client = OpenAI(
            api_key="EMPTY",
            base_url="http://localhost:8000/v1",
        )

    def generate_response(self, query, system=None):
        system_prompt = system or self.system_prompt
        try:
            # Appel à l'API vLLM en utilisant le client personnalisé
            chat_response = self.client.chat.completions.create(
                model=self.model_name or "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                temperature=0.3,
                top_p=0.3,
                max_tokens=4096,
                extra_body={
                    "repetition_penalty": 1.05,
                },
            )
            return chat_response.choices[0].message.content.strip()
        except Exception as e:
            return f"Une erreur s'est produite : {e}"