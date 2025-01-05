from .base_model import BaseLLMModel
import openai

class OpenAIModel(BaseLLMModel):
    def initialize_client(self):
        openai.api_key = self.api_key

    def generate_response(self, query, system=None):
        system_prompt = system or self.system_prompt
        response = openai.chat.completions.create(
            model=self.model_name or "o1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ],
        )
        return response.choices[0].message.content