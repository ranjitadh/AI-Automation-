import logging
from datetime import date, timedelta
from django.conf import settings
from django.db.models import Sum
from apps.billing.models import UsageEvent

logger = logging.getLogger(__name__)

MODEL_COST_PER_1K_TOKENS = {
    'gpt-4o': {'input': 0.0025, 'output': 0.01},
    'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
    'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
    'gpt-4': {'input': 0.03, 'output': 0.06},
    'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
    'text-embedding-3-small': {'input': 0.00002, 'output': 0.0},
    'text-embedding-3-large': {'input': 0.00013, 'output': 0.0},
    'text-embedding-ada-002': {'input': 0.0001, 'output': 0.0},
}

def estimate_cost(model, input_tokens, output_tokens):
    rates = MODEL_COST_PER_1K_TOKENS.get(model, {'input': 0.0025, 'output': 0.01})
    input_cost = (input_tokens / 1000) * rates['input']
    output_cost = (output_tokens / 1000) * rates['output']
    return input_cost + output_cost

def log_usage(model, input_tokens, output_tokens, endpoint='chat.completions', organization_id=None, user_id=None):
    try:
        cost_cents = round(estimate_cost(model, input_tokens, output_tokens) * 100, 4)
        quantity = max(1, int(input_tokens + output_tokens))
        UsageEvent.objects.create(
            organization_id=organization_id,
            user_id=user_id,
            event_type='openai_api_call',
            quantity=quantity,
            metadata={
                'model': model,
                'endpoint': endpoint,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'cost_cents': str(cost_cents),
                'date': str(date.today()),
            },
        )
    except Exception as e:
        logger.error(f"Failed to log OpenAI usage: {e}")

def check_daily_budget(organization_id=None):
    try:
        budget_cents = settings.OPENAI_DAILY_BUDGET_CENTS
        today_start = date.today()
        today_end = today_start + timedelta(days=1)
        filters = {
            'event_type': 'openai_api_call',
            'created_at__date': today_start,
        }
        if organization_id:
            filters['organization_id'] = organization_id
        total_usage = UsageEvent.objects.filter(**filters).aggregate(
            total=Sum('metadata__cost_cents')
        )
        used = float(total_usage['total'] or 0)
        if used >= budget_cents:
            logger.warning(
                f"Daily OpenAI budget exceeded: ${used/100:.2f} used of ${budget_cents/100:.2f} limit"
            )
            return False
        return True
    except Exception as e:
        logger.error(f"Failed to check daily budget: {e}")
        return True
