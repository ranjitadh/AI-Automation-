import re
from collections import Counter

def extract_keywords(text, min_length=3):
    if not text:
        return []
    words = re.findall(r'[a-zA-Z][a-zA-Z0-9#+.-]{2,}', text.lower())
    stop_words = {
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her',
        'was', 'one', 'our', 'out', 'has', 'have', 'been', 'some', 'same', 'also',
        'its', 'over', 'such', 'than', 'that', 'them', 'then', 'these', 'they',
        'this', 'very', 'just', 'with', 'will', 'would', 'about', 'into',
    }
    return [w for w in words if w not in stop_words and len(w) >= min_length]

def keyword_match_score(job_keywords, resume_keywords):
    if not job_keywords:
        return 100
    job_set = set(job_keywords)
    resume_set = set(resume_keywords)
    if not job_set:
        return 100
    matched = job_set & resume_set
    return round(len(matched) / len(job_set) * 100, 1)

def extract_tech_keywords(text):
    tech_patterns = [
        r'\b(python|javascript|typescript|java|golang|rust|c\+\+|ruby|php|swift)\b',
        r'\b(react|angular|vue|django|flask|spring|rails|next\.?js|node\.?js)\b',
        r'\b(postgresql|mysql|mongodb|redis|elasticsearch|cassandra|dynamodb)\b',
        r'\b(aws|azure|gcp|docker|kubernetes|terraform|ansible|jenkins)\b',
        r'\b(tensorflow|pytorch|scikit-learn|pandas|numpy)\b',
        r'\b(graphql|rest|grpc|kafka|rabbitmq|nginx|linux)\b',
    ]
    found = []
    for pattern in tech_patterns:
        found.extend(re.findall(pattern, text.lower()))
    return list(set(found))
