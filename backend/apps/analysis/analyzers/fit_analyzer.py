import logging
from apps.analysis.services import _call_gpt

logger = logging.getLogger(__name__)

def analyze_fit(job, resume=None):
    system = "You are a job fit analyst. Score how well a candidate matches a job."

    resume_context = ""
    if resume:
        resume_context = f"Resume: {resume.title} | Skills: {', '.join(s.get('name', '') for s in (resume.skills or []))} | Exp: {resume.years_of_experience}"

    prompt = f"""
Job: {job.title} @ {job.company.name}
Location: {job.location}
Description: {job.description[:2000] if job.description else 'N/A'}
Requirements: {', '.join(job.requirements or [])}
{resume_context}

Output JSON: {{"score": 0-100, "strengths": [], "gaps": [], "recommendation": "apply|skip|consider"}}
"""
    result = _call_gpt(system, prompt, {"type": "json_object"})
    return result or {"score": 50, "strengths": [], "gaps": [], "recommendation": "consider"}
