from .base_model import BaseLLMModel
import openai

class OpenAIModel(BaseLLMModel):
    def initialize_client(self):
        openai.api_key = self.api_key
        # Si vous utilisez une API base différente, définissez openai.api_base ici.

    def generate_response(self, query, system=None):
        system_prompt = system or self.system_prompt
        response = openai.openai.chat.completions.create(
            model=self.model_name or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
        )
        return response.choices[0].message.content