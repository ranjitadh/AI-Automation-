import logging
from decimal import Decimal
from datetime import timedelta

from django.utils import timezone
from django.db.models import Sum

from .models import AIRequest, AIBudget

logger = logging.getLogger(__name__)


def check_budget(organization_id: str) -> dict:
    try:
        budget = AIBudget.objects.get(organization_id=organization_id, is_active=True)
    except AIBudget.DoesNotExist:
        return {"allowed": True, "reason": "no_budget"}

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=now.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    daily = _spend_since(organization_id, today_start)
    weekly = _spend_since(organization_id, week_start)
    monthly = _spend_since(organization_id, month_start)

    result = {
        "allowed": True,
        "daily": {"spend_cents": daily, "limit_cents": budget.daily_limit_cents},
        "weekly": {"spend_cents": weekly, "limit_cents": budget.weekly_limit_cents},
        "monthly": {"spend_cents": monthly, "limit_cents": budget.monthly_limit_cents},
        "soft_limit_pct": budget.soft_limit_pct,
    }

    if daily >= budget.daily_limit_cents:
        result["allowed"] = False
        result["reason"] = "daily_limit_exceeded"
        logger.warning(f"AI daily budget exceeded for org {organization_id}: ${daily/100:.2f}")
    elif weekly >= budget.weekly_limit_cents:
        result["allowed"] = False
        result["reason"] = "weekly_limit_exceeded"
    elif monthly >= budget.monthly_limit_cents:
        result["allowed"] = False
        result["reason"] = "monthly_limit_exceeded"
    else:
        soft_daily = int(budget.daily_limit_cents * budget.soft_limit_pct / 100)
        if daily >= soft_daily:
            result["warning"] = f"soft_limit_reached ({daily}/{soft_daily})"

    return result


def _spend_since(organization_id: str, since) -> int:
    cost = (
        AIRequest.objects
        .filter(organization_id=organization_id, created_at__gte=since, status="completed")
        .aggregate(total=Sum("cost"))
    )["total"]
    if cost is None:
        return 0
    return int(float(cost) * 100)
