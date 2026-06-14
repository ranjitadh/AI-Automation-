import re
from apps.common.models import Skill

SKILL_DATABASE = {
    'python', 'javascript', 'typescript', 'java', 'go', 'golang', 'rust', 'c++', 'c#',
    'ruby', 'php', 'swift', 'kotlin', 'scala', 'perl', 'r', 'matlab',
    'react', 'angular', 'vue', 'svelte', 'next.js', 'node.js', 'express',
    'django', 'flask', 'fastapi', 'spring', 'rails', 'laravel',
    'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'cassandra', 'dynamodb',
    'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'ansible',
    'ci/cd', 'jenkins', 'github actions', 'gitlab ci', 'circleci',
    'machine learning', 'deep learning', 'nlp', 'computer vision',
    'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy',
    'graphql', 'rest', 'grpc', 'kafka', 'rabbitmq', 'nginx',
    'linux', 'unix', 'bash', 'powershell', 'git', 'agile', 'scrum',
}

def extract_skills(text):
    if not text:
        return []
    text_lower = text.lower()
    found = set()
    for skill in SKILL_DATABASE:
        if skill in text_lower:
            found.add(skill)
    db_skills = Skill.objects.filter(is_verified=True).values_list('name', flat=True)
    for skill in db_skills:
        if skill.lower() in text_lower:
            found.add(skill.lower())
    return sorted(found)

def extract_skills_from_job(job):
    text = f"{job.title} {job.description or ''} {' '.join(job.requirements or [])} {' '.join(job.nice_to_have or [])}"
    return extract_skills(text)

def extract_skills_from_resume(resume):
    text = f"{resume.summary or ''} {resume.parsed_text or ''} {' '.join(s.get('name', '') for s in (resume.skills or []))}"
    return extract_skills(text)
