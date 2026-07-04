import logging
from django.db.models import Avg, Count, Sum
from django.utils import timezone
from datetime import timedelta

from .models import AIRequest

logger = logging.getLogger(__name__)


def get_health_stats(organization_id: str = None, hours: int = 24):
    cutoff = timezone.now() - timedelta(hours=hours)
    qs = AIRequest.objects.filter(created_at__gte=cutoff)
    if organization_id:
        qs = qs.filter(organization_id=organization_id)

    total = qs.count()
    if total == 0:
        return {"total": 0, "status": "no_data"}

    failed = qs.filter(status="failed").count()
    fallback = qs.filter(status="fallback").count()

    stats = qs.aggregate(
        avg_latency=Avg("latency_ms"),
        total_cost=Sum("cost"),
        total_tokens=Sum("total_tokens"),
    )

    return {
        "total_requests": total,
        "failed": failed,
        "fallback": fallback,
        "success_rate": round((total - failed) / total * 100, 2) if total else 0,
        "avg_latency_ms": round(stats["avg_latency"] or 0, 2),
        "total_cost": float(stats["total_cost"] or 0),
        "total_tokens": int(stats["total_tokens"] or 0),
        "period_hours": hours,
    }
