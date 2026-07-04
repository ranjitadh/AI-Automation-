from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.db.models.functions import TruncWeek, TruncMonth
from django.utils import timezone
from datetime import timedelta
from apps.applications.models import Application
from apps.interviews.models import Interview, Offer
from apps.common.permissions import IsOrgMember

class DashboardView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get(self, request):
        org = request.org
        thirty_days = timezone.now() - timedelta(days=30)
        apps_qs = Application.objects.filter(organization=org)
        jobs_qs = Job.objects.all()
        interviews_qs = Interview.objects.filter(organization=org)

        total_apps = apps_qs.count()
        submitted = apps_qs.filter(status='submitted').count()
        interviews = interviews_qs.count()
        offers = Offer.objects.filter(organization=org).count()
        response_rate = (apps_qs.filter(~Q(responded_at__isnull=True)).count() / max(total_apps, 1)) * 100
        interview_rate = (interviews / max(total_apps, 1)) * 100 if total_apps else 0

        recent = apps_qs.filter(created_at__gte=thirty_days).count()
        weekly = (
            apps_qs.filter(created_at__gte=thirty_days)
            .annotate(week=TruncWeek('created_at'))
            .values('week')
            .annotate(count=Count('id'))
            .order_by('week')
        )

        return Response({
            'total_applications': total_apps,
            'submitted': submitted,
            'interviews': interviews,
            'offers': offers,
            'response_rate': round(response_rate, 1),
            'interview_rate': round(interview_rate, 1),
            'last_30_days': recent,
            'weekly_trend': list(weekly),
        })

class ApplicationAnalyticsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get(self, request):
        org = request.org
        apps = Application.objects.filter(organization=org)

        by_status = apps.values('status').annotate(count=Count('id')).order_by('status')
        by_source = apps.values('job__platform').annotate(count=Count('id')).exclude(job__platform='').order_by('-count')
        by_location = apps.values('job__location').annotate(count=Count('id')).exclude(job__location='').order_by('-count')[:20]

        return Response({
            'by_status': list(by_status),
            'by_source': list(by_source),
            'by_location': list(by_location),
        })

class FunnelView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get(self, request):
        org = request.org
        status_counts = Application.objects.filter(organization=org).values('status').annotate(count=Count('id'))
        total = 0
        stages = {}
        for item in status_counts:
            stages[item['status']] = item['count']
            total += item['count']
        for s in ('discovered', 'analyzed', 'approved', 'submitted', 'interview', 'offer'):
            stages.setdefault(s, 0)
        return Response({'total': total, 'stages': stages})

class TrendView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsOrgMember]

    def get(self, request):
        org = request.org
        period = request.query_params.get('period', 'month')
        trunc_fn = TruncMonth if period == 'month' else TruncWeek
        apps = (
            Application.objects.filter(organization=org)
            .annotate(period=trunc_fn('created_at'))
            .values('period')
            .annotate(
                total=Count('id'),
                submitted=Count('id', filter=Q(status='submitted')),
                interviews=Count('id', filter=Q(status='interview')),
            )
            .order_by('period')[:12]
        )
        return Response(list(apps))
