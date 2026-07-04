import json
import logging
from typing import Optional

from django.utils import timezone

from .gateway import generate
from .models import CareerGoal, CareerMemory, ApplicationDecision, ApplicationOutcome
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
        context["recent_decisions"] = self._get_recent_decisions()
        context["recent_outcomes"] = self._get_recent_outcomes()
        return context

    def _get_recent_decisions(self) -> list:
        return list(ApplicationDecision.objects.filter(
            user=self.user, organization=self.organization
        ).order_by('-created_at').values('decision', 'fit_score', 'auto_apply', 'created_at')[:10])

    def _get_recent_outcomes(self) -> list:
        return list(ApplicationOutcome.objects.filter(
            user=self.user, organization=self.organization
        ).order_by('-created_at').values('outcome', 'rejection_reason', 'created_at')[:10])

    def decide(self, job_data: dict) -> dict:
        context = self._build_context(job_data)
        system_prompt = (
            "You are a V2 career agent making autonomous decisions about job applications. "
            "Analyze the job against the candidate's goals, past experiences, and historical outcomes. "
            "Consider: "
            "1. Does this job align with career goals? "
            "2. Have similar jobs succeeded or failed in the past? "
            "3. Is the candidate likely to get an interview based on past patterns? "
            "4. Should this take priority over other potential applications? "
            "Return a structured decision about what action to take. "
            "Be conservative — only recommend apply when you have high confidence."
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

        parsed = result.get('parsed', result)
        if isinstance(parsed, dict) and parsed.get('action') in ('apply', 'skip', 'queue'):
            from .matching_engine import decide_application
            from ..jobs.models import Job

            job = Job.objects.filter(id=job_data.get('id')).first()
            if job:
                calibration = {"calibration_type": "maintain", "seniority_gap": "match", "changes": {}}
                fit_score = parsed.get('priority_score', 50)
                try:
                    decide_application(
                        job_match={
                            'fit_score': fit_score,
                            'confidence': parsed.get('confidence', 0.5),
                        },
                        calibration=calibration,
                        threshold=70,
                        auto_apply=(parsed.get('action') == 'apply' and parsed.get('confidence', 0) > 0.7),
                        user=self.user,
                        organization=self.organization,
                        job=job,
                    )
                except Exception as e:
                    logger.warning(f"Could not save decision: {e}")

        return result

    def should_auto_apply(self, job_data: dict) -> dict:
        result = self.decide(job_data)
        parsed = result.get('parsed', result) if isinstance(result, dict) else result

        if isinstance(parsed, dict):
            action = parsed.get('action', 'skip')
            confidence = parsed.get('confidence', 0)
            priority = parsed.get('priority_score', 0)

            can_auto = (
                action == 'apply'
                and confidence >= 0.7
                and priority >= 70
            )
            return {
                "can_auto_apply": can_auto,
                "action": action,
                "confidence": confidence,
                "priority_score": priority,
                "reasoning": parsed.get('reasoning', ''),
                "needs_review": action == 'skip' or (confidence < 0.7 and priority >= 50),
            }

        return {"can_auto_apply": False, "action": "skip", "confidence": 0, "priority_score": 0}

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
            "You are a V2 career advisor. Based on the candidate's goals, past successes, "
            "failures, and historical application patterns, provide actionable career recommendations. "
            "Consider: which industries perform best, which titles get responses, "
            "which salary ranges are realistic, and what skills to emphasize. "
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
