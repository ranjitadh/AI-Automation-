import json
import logging
import re
from typing import Optional

from .gateway import generate
from .schemas import HUMANIZED_COVER_LETTER_SCHEMA

logger = logging.getLogger(__name__)


def generate_humanized_cover_letter(job_data: dict, candidate_data: dict,
                                    style: str = 'professional',
                                    organization_id: str = None,
                                    user_id: str = None) -> dict:
    system_prompt = (
        "You are an expert cover letter writer who produces authentic, human-sounding "
        "cover letters that pass AI detection. "
        "CRITICAL RULES: "
        "1. Keep it 150-300 words — concise and impactful. "
        "2. Reference the specific company and role — show you researched them. "
        "3. Reference the candidate's actual background — be specific about projects/achievements. "
        "4. Sound like a real human wrote it — use natural transitions, vary sentence structure. "
        "5. Avoid: 'I am writing to apply for', 'I am excited to', 'I believe my skills align perfectly', "
        "   'I am confident that', buzzwords, excessive enthusiasm, robotic phrases. "
        "6. Use a confident but humble tone. Show genuine interest, not desperation. "
        "7. Never mention AI, ChatGPT, or that the letter was generated. "
        "8. Write in first person, past tense for achievements, present for current role. "
        "9. Each paragraph should flow naturally into the next. "
        "10. Include specific details that prove the candidate has done their homework "
        "    on the company's products, mission, or industry position."
    )

    style_guide = {
        'professional': 'Formal but warm. Focus on qualifications and value. '
                        'Use standard business letter structure.',
        'direct': 'Concise and straight to the point. 3-4 short paragraphs. '
                  'Lead with the most relevant qualification immediately.',
        'storytelling': 'Open with a brief, relevant anecdote or connection to the company. '
                        'Weave experience into a narrative.',
        'enthusiastic': 'Warm and genuine enthusiasm for the role and company. '
                        'Let passion show through specific examples of why this work matters.',
    }

    user_prompt = json.dumps({
        "job": {
            "title": job_data.get('title'),
            "company": job_data.get('company'),
            "description": job_data.get('description', '')[:2000],
            "requirements": job_data.get('requirements', [])[:10],
            "responsibilities": job_data.get('responsibilities', [])[:10],
            "department": job_data.get('department', ''),
            "company_industry": job_data.get('company_industry', ''),
        },
        "candidate": {
            "summary": candidate_data.get('summary', ''),
            "skills": candidate_data.get('skills', [])[:20],
            "experience": candidate_data.get('experience', [])[:5],
            "education": candidate_data.get('education', [])[:3],
            "years_of_experience": candidate_data.get('years_of_experience', 0),
        },
        "style": style,
        "style_guide": style_guide.get(style, style_guide['professional']),
        "instructions": (
            "Write a cover letter that sounds like it was written by a thoughtful, "
            "experienced professional. The reader should feel like a real person "
            "researched their company and genuinely wants this specific role. "
            "Output JSON with: subject, salutation, body_paragraphs (array of 2-4 strings), "
            "closing, full_text (the complete letter), word_count. "
            "The full_text should contain the complete letter with salutation, paragraphs, "
            "and closing as a single string."
        ),
    })

    result = generate(
        task_type='humanized_cover_letter',
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_schema=HUMANIZED_COVER_LETTER_SCHEMA,
        organization_id=organization_id,
        user_id=user_id,
    )
    return result.get('parsed', result)


def humanize_text(text: str, context: str = 'general',
                  organization_id: str = None, user_id: str = None) -> dict:
    system_prompt = (
        "You are a text humanization expert. Rewrite the given text to sound "
        "more natural, authentic, and human-written. "
        "Remove: generic AI phrases, excessive adjectives, buzzword clusters, "
        "robotic sentence structures, and unnatural enthusiasm. "
        "Keep all factual information intact. Just make it sound like a person wrote it."
    )
    user_prompt = json.dumps({
        "original_text": text,
        "context": context,
    })

    result = generate(
        task_type='humanized_cover_letter',
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        organization_id=organization_id,
        user_id=user_id,
    )
    return result.get('parsed', result)


def detect_ai_generated(text: str) -> dict:
    score, indicators = _programmatic_ai_detection(text)
    suggestions = _generate_humanization_suggestions(indicators)

    return {
        "score": round(score, 2),
        "indicators": indicators,
        "suggestions": suggestions,
        "is_likely_ai": score > 0.5,
        "detection_method": "programmatic_pattern_analysis",
    }


AI_PHRASES = [
    r'\bi am (writing|reaching out|contacting you)( to apply| regarding| about)',
    r'\bi am excited to',
    r'\bi believe my (skills|experience|qualifications) align',
    r'\bi am confident (that|my)',
    r'\bi would be (thrilled|honored|delighted)',
    r'\bproven track record\b',
    r'\bresults-driven\b',
    r'\bthought leader\b',
    r'\bpassionate about\b(?! solving)',
    r'\bteam player\b',
    r'\bgo-getter\b',
    r'\bI bring a (unique|wealth) of (experience|knowledge)',
    r'\bas you will see in my (attached|enclosed) resume',
    r'\bI have attached my resume for your (consideration|review)',
    r'\bI look forward to the (opportunity|possibility) of discussing',
    r'\bplease find (attached|enclosed)',
    r'\bdynamic and (fast-paced|results-oriented)',
    r'\bbest (regards|wishes)',
]

TRANSITION_PATTERNS = [
    r'\bin addition\b',
    r'\bfurthermore\b',
    r'\bmoreover\b',
    r'\badditionally\b',
    r'\bconsequently\b',
    r'\bnevertheless\b',
    r'\bnotwithstanding\b',
]

BUZZWORD_CLUSTERS = [
    'synergy', 'leverage', 'optimize', 'streamline', 'utilize',
    'holistic', 'robust', 'scalable', 'innovative', 'paradigm',
    'cutting-edge', 'world-class', 'best-in-class', 'best-in-breed',
    'low-hanging fruit', 'move the needle', 'drill down',
    'circle back', 'touch base', 'deep dive',
]


def _programmatic_ai_detection(text: str):
    text_lower = text.lower()
    indicators = []
    total_score = 0.0

    ai_phrase_matches = []
    for pattern in AI_PHRASES:
        matches = re.findall(pattern, text_lower)
        if matches:
            ai_phrase_matches.extend(matches)
            indicators.append(f"AI phrase detected: '{matches[0]}'")

    if ai_phrase_matches:
        score_from_phrases = min(0.3, len(ai_phrase_matches) * 0.05)
        total_score += score_from_phrases
        if len(ai_phrase_matches) >= 3:
            indicators.append(f"Multiple AI phrases ({len(ai_phrase_matches)}) — strong AI signal")

    transition_matches = []
    for pattern in TRANSITION_PATTERNS:
        matches = re.findall(pattern, text_lower)
        if matches:
            transition_matches.extend(matches)

    if len(transition_matches) >= 3:
        total_score += 0.15
        indicators.append(f"Overuse of formal transitions ({len(transition_matches)}) — AI hallmark")

    buzzword_count = 0
    for word in BUZZWORD_CLUSTERS:
        if word in text_lower:
            buzzword_count += 1

    if buzzword_count >= 2:
        total_score += 0.15
        indicators.append(f"Buzzword cluster ({buzzword_count} buzzwords) — generic AI writing")

    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if sentences:
        avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
        if 18 <= avg_length <= 22:
            total_score += 0.1
            indicators.append(f"Average sentence length ~{avg_length:.0f} words — AI-like consistency")

        lengths = [len(s.split()) for s in sentences]
        if lengths:
            variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
            if variance < 15:
                total_score += 0.1
                indicators.append(f"Low sentence length variance ({variance:.0f}) — robotic consistency")

        para_transitions = 0
        for i, s in enumerate(sentences[1:], 1):
            first_word = s.split()[0].lower() if s.split() else ''
            if first_word in ['however', 'therefore', 'thus', 'hence', 'indeed', 'moreover', 'furthermore']:
                para_transitions += 1

        if para_transitions >= 2:
            total_score += 0.1
            indicators.append(f"Multiple paragraphs start with formal transition words")

    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if len(paragraphs) == 3:
        total_score += 0.05
        indicators.append("Exactly 3 paragraphs — common AI structure")

    word_count = len(text.split())
    if 180 <= word_count <= 220:
        total_score += 0.05
        indicators.append(f"Word count ~{word_count} — near LLM default length")

    total_score = min(1.0, total_score)

    return total_score, indicators


def _generate_humanization_suggestions(indicators: list) -> list:
    suggestions = []
    phrase_indicators = [i for i in indicators if 'AI phrase' in i]
    if phrase_indicators:
        suggestions.append("Replace AI phrases with specific, concrete statements about your actual work")

    buzzword_indicators = [i for i in indicators if 'buzzword' in i]
    if buzzword_indicators:
        suggestions.append("Remove generic buzzwords and replace with specific technical terms or metrics")

    sentence_indicators = [i for i in indicators if 'sentence' in i]
    if sentence_indicators:
        suggestions.append("Vary sentence length: mix short punchy sentences with longer explanatory ones")

    transition_indicators = [i for i in indicators if 'transition' in i]
    if transition_indicators:
        suggestions.append("Reduce formal transition words; let paragraphs flow naturally without 'however'/'furthermore'")

    para_indicators = [i for i in indicators if 'paragraphs' in i or 'structure' in i]
    if para_indicators:
        suggestions.append("Vary paragraph structure — not all 3-paragraph letters need identical format")

    if not suggestions:
        suggestions.append("Text appears natural — minor improvements may still help")
        suggestions.append("Add a specific, personal detail that only a real applicant would know")

    return suggestions
