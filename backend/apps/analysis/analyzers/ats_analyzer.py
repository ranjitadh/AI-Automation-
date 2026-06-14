from apps.analysis.services import _call_gpt

def analyze_ats_compatibility(job_description, resume_text):
    system = """You are an ATS (Applicant Tracking System) expert. Analyze resume against job description.
Return JSON with score and improvement suggestions."""

    prompt = f"""
Job Description:
{job_description[:3000]}

Resume:
{resume_text[:3000]}

Analyze ATS compatibility.
Output JSON: {{"score": 0-100, "keyword_match_pct": 0.0, "missing_keywords": [], "formatting_issues": [], "suggestions": []}}
"""
    return _call_gpt(system, prompt, {"type": "json_object"})
