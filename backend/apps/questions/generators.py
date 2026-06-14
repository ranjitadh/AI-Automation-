from apps.analysis.services import _call_gpt

QUESTION_CATEGORIES = {
    'sponsorship': 'Do you now or will you in the future require visa sponsorship?',
    'salary': 'What are your salary expectations?',
    'experience': 'How many years of experience do you have?',
    'remote': 'Are you willing to work from the office?',
    'relocation': 'Are you willing to relocate?',
    'start_date': 'When can you start?',
    'why_company': 'Why do you want to work here?',
    'why_role': 'Why are you interested in this role?',
    'strengths': 'What are your greatest strengths?',
    'weaknesses': 'What are your areas for improvement?',
    'security_clearance': 'Do you have an active security clearance?',
    'education': 'What is your highest level of education?',
}

def generate_answer(question, job=None):
    system = """You are helping a job applicant answer screening questions.
Provide natural, honest, professional answers that match the candidate's background.
Return just the answer text, no JSON, no explanation."""

    context = ""
    if job:
        context = f"Job: {job.title} @ {job.company.name}\nDescription: {(job.description or '')[:1000]}\n"

    prompt = f"""{context}
Question: {question.question}
Category: {question.category}

Write a professional, concise answer (1-3 sentences) that a real job applicant would give.
Be honest but strategic. Assume the candidate has 5+ years of relevant experience.
"""

    return _call_gpt(system, prompt)
