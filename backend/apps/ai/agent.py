import json
import logging
from typing import Optional

from django.utils import timezone

from .gateway import generate
from .models import CareerGoal, CareerMemory
from .services import _get_prompt
from .schemas import CAREER_AGENT_DECISION_SCHEMA

logger = logging.getLogger(__name__)


class CareerAgent:
    def __init__(self, user, organization):
        self.user = user
        self.organization = organization
        self.goals = self._load_goals()
        self.memories = self._load_memories()

    def _load_goals(self) -> Optional[CareerGoal]:
        return CareerGoal.objects.filter(
            user=self.user, organization=self.organization, is_active=True
        ).first()

    def _load_memories(self) -> list:
        return list(CareerMemory.objects.filter(
            user=self.user, organization=self.organization, is_active=True
        ).order_by('-confidence')[:50])

    def _build_context(self, job_data: dict = None) -> dict:
        context = {
            "goals": {
                "target_titles": self.goals.target_titles if self.goals else [],
                "target_salary_min": self.goals.target_salary_min if self.goals else None,
                "target_salary_max": self.goals.target_salary_max if self.goals else None,
                "target_companies": self.goals.target_companies if self.goals else [],
                "target_locations": self.goals.target_locations if self.goals else [],
                "remote_preference": self.goals.remote_preference if self.goals else "any",
                "seniority_level": self.goals.seniority_level if self.goals else None,
            },
            "memories": [
                {"type": m.memory_type, "key": m.key, "value": m.value, "confidence": m.confidence}
                for m in self.memories
            ],
        }
        if job_data:
            context["job"] = job_data
        return context

    def decide(self, job_data: dict) -> dict:
        context = self._build_context(job_data)
        system_prompt = (
            "You are a career agent making autonomous decisions about job applications. "
            "Analyze the job against the candidate's goals and past experiences. "
            "Return a structured decision about what action to take."
        )
        user_prompt = json.dumps(context, indent=2)

        result = generate(
            task_type='career_agent_reasoning',
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=CAREER_AGENT_DECISION_SCHEMA,
            organization_id=str(self.organization.id),
            user_id=str(self.user.id),
        )
        return result

    def learn(self, outcome: dict):
        memory_type = 'success_pattern' if outcome.get('success') else 'failure_pattern'
        key = outcome.get('pattern_key', outcome.get('type', 'observation'))
        CareerMemory.objects.update_or_create(
            user=self.user,
            organization=self.organization,
            memory_type=memory_type,
            key=key,
            defaults={
                'value': outcome.get('data', {}),
                'confidence': outcome.get('confidence', 0.5),
                'source': outcome.get('source', 'agent'),
            },
        )

    def get_recommendations(self, limit: int = 5) -> list:
        prompt = _get_prompt('career_agent_reasoning', None)
        context = self._build_context()
        system_prompt = (
            "You are a career advisor. Based on the candidate's goals, past successes, "
            "and failures, provide actionable career recommendations. "
            "Return a JSON object with a 'recommendations' array."
        )
        user_prompt = json.dumps(context, indent=2)

        result = generate(
            task_type='career_agent_reasoning',
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            organization_id=str(self.organization.id),
            user_id=str(self.user.id),
        )
        return result.get('parsed', result)
