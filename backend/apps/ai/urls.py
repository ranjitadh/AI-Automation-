from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'requests', views.AIRequestViewSet, basename='ai-request')
router.register(r'prompts', views.PromptTemplateViewSet, basename='ai-prompt')
router.register(r'budgets', views.AIBudgetViewSet, basename='ai-budget')
router.register(r'goals', views.CareerGoalViewSet, basename='career-goal')
router.register(r'memories', views.CareerMemoryViewSet, basename='career-memory')
router.register(r'decisions', views.ApplicationDecisionViewSet, basename='application-decision')
router.register(r'outcomes', views.ApplicationOutcomeViewSet, basename='application-outcome')

urlpatterns = [
    path('', include(router.urls)),
    path('generate/', views.AIGenerateView.as_view(), name='ai-generate'),
    path('agent/decide/', views.AgentDecisionView.as_view(), name='agent-decide'),
    path('agent/recommendations/', views.AgentRecommendationsView.as_view(), name='agent-recommendations'),
    path('analyze/fit/', views.FitScoreView.as_view(), name='ai-fit-score'),
    path('analyze/optimize-resume/', views.ResumeOptimizeView.as_view(), name='ai-optimize-resume'),
    path('analyze/interview-prep/', views.InterviewPrepView.as_view(), name='ai-interview-prep'),
    path('analyze/job-match/', views.JobMatchAnalyzeView.as_view(), name='ai-job-match'),
    path('analyze/patterns/', views.AnalyzePatternsView.as_view(), name='ai-analyze-patterns'),
    path('resume/adapt/', views.ResumeAdaptView.as_view(), name='ai-resume-adapt'),
    path('cover-letter/generate/', views.HumanizedCoverLetterView.as_view(), name='ai-cover-letter'),
    path('questions/answer/', views.ScreeningAnswersView.as_view(), name='ai-screening-answers'),
    path('validate/', views.ValidateApplicationView.as_view(), name='ai-validate'),
    path('calibrate/', views.CalibrateExperienceView.as_view(), name='ai-calibrate'),
    path('outcomes/record/', views.RecordOutcomeView.as_view(), name='ai-record-outcome'),
    path('outcomes/weekly-report/', views.WeeklyReportView.as_view(), name='ai-weekly-report'),
    path('check-consistency/', views.ConsistencyCheckView.as_view(), name='ai-check-consistency'),
    path('simulate/recruiter/', views.RecruiterSimulationView.as_view(), name='ai-recruiter-simulation'),
    path('evaluate/quality/', views.ApplicationQualityView.as_view(), name='ai-application-quality'),
    path('evaluate/ats/', views.ATSOptimizationView.as_view(), name='ai-ats-optimization'),
    path('maximize/interview/', views.InterviewMaximizationView.as_view(), name='ai-interview-maximization'),
    path('analytics/', views.AIAnalyticsView.as_view(), name='ai-analytics'),
    path('prompts/rollback/', views.PromptTemplateViewSet.as_view({'post': 'rollback'}), name='ai-prompt-rollback'),
]
