import time
import logging
from typing import Optional
from decimal import Decimal

from django.conf import settings

from .base import BaseAIProvider, ProviderResponse

logger = logging.getLogger(__name__)

OPENAI_COST_PER_1K = {
    'gpt-4o': {'input': 0.00250, 'output': 0.01000},
    'gpt-4o-mini': {'input': 0.00015, 'output': 0.00060},
    'gpt-4-turbo': {'input': 0.01000, 'output': 0.03000},
}


class OpenAIProvider(BaseAIProvider):
    provider_name = 'openai'

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self._client = None

    @property
    def default_model(self):
        return settings.OPENAI_MODEL

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def generate(self, system_prompt: str, user_prompt: str,
                 temperature: float = 0.3, max_tokens: int = 4096,
                 response_schema: Optional[dict] = None,
                 model: Optional[str] = None) -> ProviderResponse:
        model_name = self.get_model_name(model)
        client = self._get_client()
        start = time.time()

        try:
            kwargs = {
                'model': model_name,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                'temperature': temperature,
                'max_tokens': max_tokens,
            }
            if response_schema:
                kwargs['response_format'] = {'type': 'json_object'}

            response = client.chat.completions.create(**kwargs)

            latency = int((time.time() - start) * 1000)
            choice = response.choices[0] if response.choices else None
            text = choice.message.content if choice else ''
            usage = response.usage

            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0

            cost = self._calculate_cost(model_name, prompt_tokens, completion_tokens)

            return ProviderResponse(
                content=text,
                model=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost,
                latency_ms=latency,
                provider='openai',
            )
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            return ProviderResponse(
                content='', model=model_name, latency_ms=latency,
                provider='openai', error=str(e),
            )

    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(model or self.default_model)
            return len(encoding.encode(text))
        except Exception:
            return len(text.split()) * 2

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        rates = OPENAI_COST_PER_1K.get(model, OPENAI_COST_PER_1K['gpt-4o-mini'])
        input_cost = (input_tokens / 1000) * rates['input']
        output_cost = (output_tokens / 1000) * rates['output']
        return float(Decimal(str(input_cost + output_cost)).quantize(Decimal('0.000001')))
