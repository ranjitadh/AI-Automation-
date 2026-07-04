from decimal import Decimal
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from datetime import timedelta

from .models import AIRequest


def get_daily_usage(organization_id: str, days: int = 30):
    cutoff = timezone.now() - timedelta(days=days)
    return (
        AIRequest.objects
        .filter(organization_id=organization_id, created_at__gte=cutoff)
        .extra({"date": "date(created_at)"})
        .values("date")
        .annotate(
            total_requests=Count("id"),
            total_cost=Sum("cost"),
            avg_latency=Avg("latency_ms"),
            total_tokens=Sum("total_tokens"),
            failed=Count("id", filter=models.Q(status="failed")),
        )
        .order_by("date")
    )


def get_task_type_breakdown(organization_id: str, days: int = 30):
    cutoff = timezone.now() - timedelta(days=days)
    return (
        AIRequest.objects
        .filter(organization_id=organization_id, created_at__gte=cutoff)
        .values("task_type")
        .annotate(
            count=Count("id"),
            total_cost=Sum("cost"),
            avg_latency=Avg("latency_ms"),
        )
        .order_by("-total_cost")
    )


def get_total_spend(organization_id: str, since: timezone.datetime = None):
    qs = AIRequest.objects.filter(organization_id=organization_id)
    if since:
        qs = qs.filter(created_at__gte=since)
    return qs.aggregate(
        total=Sum("cost"),
        count=Count("id"),
        avg_tokens=Avg("total_tokens"),
    )


def get_provider_breakdown(organization_id: str, days: int = 30):
    cutoff = timezone.now() - timedelta(days=days)
    return (
        AIRequest.objects
        .filter(organization_id=organization_id, created_at__gte=cutoff)
        .values("provider", "model")
        .annotate(
            count=Count("id"),
            total_cost=Sum("cost"),
            avg_latency=Avg("latency_ms"),
            total_tokens=Sum("total_tokens"),
        )
        .order_by("provider", "model")
    )


import django.db.models as models
