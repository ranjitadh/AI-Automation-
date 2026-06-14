import json
from apps.analysis.services import _call_gpt

STYLES = {
    'short': 'Write a very concise cover letter of 2-3 paragraphs (100-150 words). Be direct and impactful.',
    'medium': 'Write a professional cover letter of 3-4 paragraphs (200-300 words). Include an opening, body, and closing.',
    'long': 'Write a comprehensive cover letter of 4-5 paragraphs (350-500 words). Include detailed examples and qualifications.',
    'custom': None,
}

def generate_cover_letter(job, resume=None, style='medium'):
    style_instruction = STYLES.get(style, STYLES['medium'])

    system = f"""You are a professional cover letter writer. {style_instruction}

Return JSON:
{{
  "subject": "Application for {job.title}",
  "salutation": "Dear Hiring Manager,",
  "body": "Full cover letter text...",
  "closing": "Sincerely,"
}}"""

    resume_context = ""
    if resume:
        resume_context = f"""
Resume Title: {resume.title}
Summary: {resume.summary or 'N/A'}
Skills: {', '.join(s.get('name', '') for s in (resume.skills or []))}
Experience: {json.dumps(resume.experience or [])}
Education: {json.dumps(resume.education or [])}
"""

    prompt = f"""
Job Title: {job.title}
Company: {job.company.name}
Location: {job.location or 'N/A'}
Description: {job.description[:2000] if job.description else 'N/A'}
Requirements: {', '.join(job.requirements or [])}

{resume_context}

Write a {'professional' if style != 'custom' else ''} cover letter tailored to this job and candidate.
No placeholders. No AI disclaimers. Write in first person.
"""

    return _call_gpt(system, prompt, {"type": "json_object"})
