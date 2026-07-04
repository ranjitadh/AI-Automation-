import time
import json
import logging
from decimal import Decimal
from typing import Optional, Type

from django.conf import settings

from .providers.base import BaseAIProvider
from .providers.gemini import GeminiProvider
from .providers.openai import OpenAIProvider
from .models import AIRequest

logger = logging.getLogger(__name__)

ROUTING_TABLE = {
    'job_parsing': {'provider': 'gemini', 'model': 'gemini-2.5-flash'},
    'resume_parsing': {'provider': 'gemini', 'model': 'gemini-2.5-flash'},
    'skill_extraction': {'provider': 'gemini', 'model': 'gemini-2.5-flash'},
    'company_analysis': {'provider': 'gemini', 'model': 'gemini-2.5-flash'},
    'classification': {'provider': 'gemini', 'model': 'gemini-2.5-flash'},
    'tagging': {'provider': 'gemini', 'model': 'gemini-2.5-flash'},
    'bulk_processing': {'provider': 'gemini', 'model': 'gemini-2.5-flash'},
    'ats_analysis': {'provider': 'gemini', 'model': 'gemini-2.5-pro'},
    'resume_optimization': {'provider': 'gemini', 'model': 'gemini-2.5-pro'},
    'resume_adaptation': {'provider': 'gemini', 'model': 'gemini-2.5-pro'},
    'career_agent_reasoning': {'provider': 'gemini', 'model': 'gemini-2.5-pro'},
    'interview_preparation': {'provider': 'gemini', 'model': 'gemini-2.5-pro'},
    'cover_letter': {'provider': 'gemini', 'model': 'gemini-2.5-pro'},
    'humanized_cover_letter': {'provider': 'gemini', 'model': 'gemini-2.5-pro'},
    'question_answering': {'provider': 'gemini', 'model': 'gemini-2.5-flash'},
    'screening_answer': {'provider': 'gemini', 'model': 'gemini-2.5-flash'},
    'fit_scoring': {'provider': 'gemini', 'model': 'gemini-2.5-pro'},
    'application_decision': {'provider': 'gemini', 'model': 'gemini-2.5-pro'},
    'application_validation': {'provider': 'gemini', 'model': 'gemini-2.5-flash'},
    'experience_calibration': {'provider': 'gemini', 'model': 'gemini-2.5-pro'},
    'decision_making': {'provider': 'gemini', 'model': 'gemini-2.5-pro'},
    'learning_insight': {'provider': 'gemini', 'model': 'gemini-2.5-pro'},
    'learning_outcome': {'provider': 'gemini', 'model': 'gemini-2.5-pro'},
    'consistency_check': {'provider': 'gemini', 'model': 'gemini-2.5-flash'},
}

_providers: dict[str, BaseAIProvider] = {}


def _get_provider(provider_name: str) -> BaseAIProvider:
    if provider_name not in _providers:
        registry = {
            'gemini': GeminiProvider,
            'openai': OpenAIProvider,
        }
        cls = registry.get(provider_name)
        if not cls:
            raise ValueError(f"Unknown provider: {provider_name}")
        _providers[provider_name] = cls()
    return _providers[provider_name]


def generate(task_type: str, system_prompt: str, user_prompt: str,
             temperature: Optional[float] = None, max_tokens: Optional[int] = None,
             response_schema: Optional[dict] = None,
             model: Optional[str] = None, provider: Optional[str] = None,
             organization_id: Optional[str] = None, user_id: Optional[str] = None,
             prompt_name: Optional[str] = None,
             max_retries: int = 2, fallback_provider: Optional[str] = None) -> dict:
    route = ROUTING_TABLE.get(task_type, {'provider': 'gemini', 'model': 'gemini-2.5-flash'})
    provider_name = provider or route['provider']
    model_name = model or route['model']
    temp = temperature if temperature is not None else 0.3
    tokens = max_tokens if max_tokens is not None else 4096

    last_error = None
    attempts = 0

    providers_to_try = [provider_name]
    if fallback_provider and fallback_provider != provider_name:
        providers_to_try.append(fallback_provider)

    for attempt_provider in providers_to_try:
        for attempt in range(max_retries + 1):
            attempts += 1
            try:
                p = _get_provider(attempt_provider)
                resp = p.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temp,
                    max_tokens=tokens,
                    response_schema=response_schema,
                    model=model_name,
                )

                request_record = AIRequest.objects.create(
                    organization_id=organization_id,
                    user_id=user_id,
                    task_type=task_type,
                    provider=resp.provider or attempt_provider,
                    model=resp.model,
                    prompt_tokens=resp.prompt_tokens,
                    completion_tokens=resp.completion_tokens,
                    total_tokens=resp.total_tokens,
                    cost=Decimal(str(resp.cost)),
                    latency_ms=resp.latency_ms,
                    status='completed' if not resp.error else 'failed',
                    error=resp.error,
                    prompt_id=prompt_name,
                )

                if resp.error:
                    last_error = resp.error
                    if attempt < max_retries:
                        continue
                    return {'error': resp.error, 'request_id': str(request_record.id)}

                result = {'content': resp.content, 'request_id': str(request_record.id)}
                if response_schema and resp.content:
                    try:
                        parsed = json.loads(resp.content)
                        result['parsed'] = parsed
                    except json.JSONDecodeError:
                        result['parsed'] = None
                return result

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Gateway attempt {attempts} failed ({attempt_provider}/{model_name}): {e}")
                if attempt < max_retries:
                    continue
                break

    AIRequest.objects.create(
        organization_id=organization_id,
        user_id=user_id,
        task_type=task_type,
        provider=provider_name,
        model=model_name,
        status='failed',
        error=last_error,
        prompt_id=prompt_name,
    )
    return {'error': last_error}


def count_tokens(text: str, task_type: str = 'bulk_processing') -> int:
    route = ROUTING_TABLE.get(task_type, {'provider': 'gemini', 'model': 'gemini-2.5-flash'})
    p = _get_provider(route['provider'])
    return p.count_tokens(text)
