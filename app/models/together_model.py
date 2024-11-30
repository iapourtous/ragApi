from .base_model import BaseLLMModel
from together import Together
import logging

class TogetherModel(BaseLLMModel):
    def initialize_client(self):
        self.client = Together()

    def generate_response(self, query, system=None):
        system_prompt = system or self.system_prompt
        try:
            response = self.client.chat.completions.create(
                model=self.model_name or "Qwen/Qwen2.5-72B-Instruct-Turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                max_tokens=8192,
                temperature=0.1,
                top_p=0.7,
                top_k=50,
                repetition_penalty=1.0,
                stop=["<|im_end|>"],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Erreur avec TogetherModel : {e}")
            raise e