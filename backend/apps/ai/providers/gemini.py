import time
import logging
from typing import Optional
from decimal import Decimal

from django.conf import settings

from .base import BaseAIProvider, ProviderResponse

logger = logging.getLogger(__name__)

GEMINI_COST_PER_1K = {
    'gemini-2.5-pro': {'input': 0.00125, 'output': 0.00500},
    'gemini-2.5-flash': {'input': 0.00015, 'output': 0.00060},
    'gemini-2.0-flash': {'input': 0.00010, 'output': 0.00040},
}


class GeminiProvider(BaseAIProvider):
    provider_name = 'gemini'

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self._client = None

    @property
    def default_model(self):
        return 'gemini-2.5-flash'

    def _get_client(self):
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai
            except ImportError:
                raise ImportError("google-generativeai is not installed. pip install google-generativeai")
        return self._client

    def generate(self, system_prompt: str, user_prompt: str,
                 temperature: float = 0.3, max_tokens: int = 4096,
                 response_schema: Optional[dict] = None,
                 model: Optional[str] = None) -> ProviderResponse:
        model_name = self.get_model_name(model)
        client = self._get_client()
        start = time.time()

        try:
            gen_model = client.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt,
                generation_config={
                    'temperature': temperature,
                    'max_output_tokens': max_tokens,
                },
            )
            response = gen_model.generate_content(user_prompt)

            latency = int((time.time() - start) * 1000)
            text = response.text if hasattr(response, 'text') else ''

            usage = getattr(response, 'usage_metadata', None)
            prompt_tokens = usage.prompt_token_count if usage else 0
            completion_tokens = usage.candidates_token_count if usage else 0
            total_tokens = usage.total_token_count if usage else 0

            cost = self._calculate_cost(model_name, prompt_tokens, completion_tokens)

            return ProviderResponse(
                content=text,
                model=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=latency,
                provider='gemini',
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            logger.error(f"Gemini API error: {e}", exc_info=True)
            return ProviderResponse(
                content='', model=model_name, latency_ms=latency,
                provider='gemini', error=str(e),
            )

    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        model_name = self.get_model_name(model)
        try:
            client = self._get_client()
            gen_model = client.GenerativeModel(model_name)
            response = gen_model.count_tokens(text)
            return response.total_tokens if hasattr(response, 'total_tokens') else 0
        except Exception as e:
            logger.warning(f"Gemini token count failed: {e}")
            return 0

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        rates = GEMINI_COST_PER_1K.get(model, GEMINI_COST_PER_1K['gemini-2.5-flash'])
        input_cost = (input_tokens / 1000) * rates['input']
        output_cost = (output_tokens / 1000) * rates['output']
        return float(Decimal(str(input_cost + output_cost)).quantize(Decimal('0.000001')))
