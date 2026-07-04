import json
import logging
import random
import re
from typing import Optional, Tuple

from .gateway import generate
from .schemas import HUMANIZED_COVER_LETTER_SCHEMA

logger = logging.getLogger(__name__)


V2_PHRASE_REPLACEMENTS = {
    "i am writing to apply for": ["i'm interested in the", "the", "regarding the"],
    "i am writing to express my interest": ["i'd like to be considered for", "i'm reaching out about"],
    "i am excited to apply": ["i was excited to see", "the caught my eye"],
    "i am thrilled to": ["i'm eager to", "i'd love to"],
    "i am confident that my skills": ["my background in", "my experience with"],
    "i believe my skills align": ["my experience maps well to", "what i've worked on aligns with"],
    "proven track record": ["experience", "background", "work"],
    "i am a highly motivated": ["i'm a", "i'm an experienced"],
    "please find attached": ["i've attached", "my resume is attached"],
    "i have attached my resume": ["my resume is attached", "attached is my resume"],
    "i look forward to hearing from you": ["i'd welcome the chance to discuss", "i'm available to discuss"],
    "thank you for your time and consideration": ["thank you for your time", "thanks for reviewing my application"],
    "i am passionate about": ["i enjoy", "i focus on", "my interest is in"],
    "i possess the": ["i have", "my background includes"],
    "as you can see from my": ["my resume shows", "most recently"],
}


COVER_LETTER_TEMPLATES = [
    # Template 0: Direct experience match
    lambda j, c: (
        f"Subject: {c.get('years_of_experience', 'Experienced')} {j.get('title')} — {j.get('company')}\n\n"
        f"Hi {j.get('company')} team,\n\n"
        f"I've been following {j.get('company')}'s work in {j.get('company_industry', 'the industry')} for a while, "
        f"and when I saw the {j.get('title')} role, it felt like a natural fit. "
        f"Most of my recent work has been in this space — {candidate_skill_summary(c)} — "
        f"and I'm genuinely excited about what your team is building.\n\n"
        f"One project I'm particularly proud of: {candidate_project_summary(c)}. "
        f"That experience maps directly to what you're looking for in this role. "
        f"I'd love to bring that same approach to {j.get('company')}.\n\n"
        f"I'd welcome the chance to chat about how my background aligns with your needs.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 1: Industry passion
    lambda j, c: (
        f"Subject: {j.get('title')} at {j.get('company')}\n\n"
        f"Hello,\n\n"
        f"The {j.get('title')} position at {j.get('company')} caught my eye — "
        f"specifically because of your focus on {j.get('company_industry', 'quality engineering')}. "
        f"I've spent the last {c.get('years_of_experience', 'several')} years working on "
        f"{candidate_skill_summary(c)}, and I'm at a point where I want to apply that experience "
        f"to a team doing meaningful work.\n\n"
        f"In my current role, {candidate_project_summary(c)}. "
        f"I'm looking for a place where I can dive deeper, and {j.get('company')} seems like exactly that place.\n\n"
        f"Happy to chat anytime.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 2: Career pivot
    lambda j, c: (
        f"Subject: {j.get('title')} — {c.get('name', 'Applicant')}\n\n"
        f"Hi there,\n\n"
        f"I'm writing about the {j.get('title')} role at {j.get('company')}. "
        f"My background is in {candidate_skill_summary(c)}, and I've been actively moving toward "
        f"the kind of work you're doing. "
        f"The fit isn't perfect on paper, but my experience with {candidate_project_summary(c)} "
        f"gives me a solid foundation to contribute from day one.\n\n"
        f"I'm particularly drawn to how {j.get('company')} approaches "
        f"{j.get('company_industry', 'product development')}. "
        f"I'd love to discuss how my skills could translate.\n\n"
        f"Thanks for your time.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 3: Short and direct
    lambda j, c: (
        f"Subject: {j.get('title')} application — {c.get('name', 'Applicant')}\n\n"
        f"Hi,\n\n"
        f"I'm applying for the {j.get('title')} role at {j.get('company')}. "
        f"My background: {candidate_skill_summary(c)} across "
        f"{c.get('years_of_experience', 'several')} years. "
        f"Most relevant: {candidate_project_summary(c)}.\n\n"
        f"I'd love to talk about how I can contribute.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 4: Results-focused
    lambda j, c: (
        f"Subject: {j.get('title')} — {c.get('name', 'Applicant')}\n\n"
        f"Hello {j.get('company')} team,\n\n"
        f"Results matter. Here's what I've done recently: {candidate_project_summary(c)}. "
        f"I'm looking to do similar work at {j.get('company')} as your next {j.get('title')}.\n\n"
        f"My skills in {candidate_skill_summary(c)} directly align with what you need for this role. "
        f"I'd welcome the chance to walk through my approach.\n\n"
        f"Thanks,\n{c.get('name', 'Applicant')}"
    ),
    # Template 5: Culture-focused
    lambda j, c: (
        f"Subject: Excited about the {j.get('title')} role\n\n"
        f"Hi,\n\n"
        f"I've read a lot about {j.get('company')}'s culture around "
        f"{j.get('company_industry', 'engineering excellence')}, and it resonates. "
        f"I've spent {c.get('years_of_experience', 'several')} years building "
        f"{candidate_skill_summary(c)}, and I believe in shipping quality work — "
        f"something your team clearly values.\n\n"
        f"One example: {candidate_project_summary(c)}. "
        f"I'd bring that same ownership mindset to your team.\n\n"
        f"Would love to chat.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 6: Problem-solving
    lambda j, c: (
        f"Subject: {j.get('title')} — solving hard problems\n\n"
        f"Hi {j.get('company')} team,\n\n"
        f"Hard problems are what drive me. The {j.get('title')} role at {j.get('company')} "
        f"looks like the kind of challenge I've been preparing for. "
        f"My work on {candidate_project_summary(c)} required "
        f"{candidate_skill_summary(c)}, and I'm excited to take that further.\n\n"
        f"I'd love to talk about specific problems your team is tackling.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 7: Growth-oriented
    lambda j, c: (
        f"Subject: {j.get('title')} — {c.get('name', 'Applicant')}\n\n"
        f"Hello,\n\n"
        f"I'm looking for a role where I can grow and contribute meaningfully — "
        f"the {j.get('title')} at {j.get('company')} seems like that opportunity. "
        f"With {c.get('years_of_experience', 'my')} years in "
        f"{candidate_skill_summary(c)}, I've built a solid foundation. "
        f"What excites me about {j.get('company')} is {j.get('company_industry', 'your approach to building')}.\n\n"
        f"My recent work on {candidate_project_summary(c)} shows what I can deliver. "
        f"I'd love to bring that to your team.\n\n"
        f"Thanks for considering my application.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 8: Mentor/leadership angle
    lambda j, c: (
        f"Subject: {j.get('title')} application\n\n"
        f"Hi,\n\n"
        f"Beyond just building things, I care about how teams work. "
        f"As someone with {c.get('years_of_experience', 'extensive')} years in "
        f"{candidate_skill_summary(c)}, I've learned that the best results come from "
        f"collaboration and clear communication. "
        f"That's why {j.get('company')}'s approach to {j.get('company_industry', 'engineering')} appeals to me.\n\n"
        f"A recent example: {candidate_project_summary(c)}. "
        f"I'd love to bring my experience to your {j.get('title')} role.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 9: Technical deep-dive
    lambda j, c: (
        f"Subject: {j.get('title')} — {c.get('name', 'Applicant')}\n\n"
        f"Hi {j.get('company')} team,\n\n"
        f"I've been working extensively with {candidate_skill_summary(c)}, "
        f"and the {j.get('title')} role looks like a great match. "
        f"Specifically, my experience with {candidate_project_summary(c)} "
        f"directly applies to what you're building.\n\n"
        f"I'm particularly interested in how {j.get('company')} tackles "
        f"{j.get('company_industry', 'scalability and reliability')}. "
        f"I'd love to discuss how my background fits.\n\n"
        f"Thanks,\n{c.get('name', 'Applicant')}"
    ),
    # Template 10: Customer/user-focused
    lambda j, c: (
        f"Subject: {j.get('title')} — user focus\n\n"
        f"Hello,\n\n"
        f"What draws me to {j.get('company')} is the emphasis on user experience in "
        f"{j.get('company_industry', 'product development')}. "
        f"I've spent {c.get('years_of_experience', 'years')} building "
        f"{candidate_skill_summary(c)} with a focus on what users actually need. "
        f"Most recently, {candidate_project_summary(c)}.\n\n"
        f"I'd love to bring that user-first mentality to your team as your next {j.get('title')}.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 11: Efficiency/optimization
    lambda j, c: (
        f"Subject: {j.get('title')} — building better systems\n\n"
        f"Hi,\n\n"
        f"I'm all about building systems that work well and don't break. "
        f"The {j.get('title')} role at {j.get('company')} caught my attention because "
        f"I've spent {c.get('years_of_experience', 'years')} doing exactly that with "
        f"{candidate_skill_summary(c)}.\n\n"
        f"Example: {candidate_project_summary(c)}. "
        f"I'd approach your challenges with the same mindset.\n\n"
        f"Happy to discuss further.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 12: Collaborative
    lambda j, c: (
        f"Subject: {j.get('title')} — teamwork and impact\n\n"
        f"Hello {j.get('company')} team,\n\n"
        f"Good products come from good teams. "
        f"I'm interested in the {j.get('title')} role because I believe my experience with "
        f"{candidate_skill_summary(c)} combined with strong collaboration skills "
        f"would let me contribute from day one.\n\n"
        f"One thing I worked on recently: {candidate_project_summary(c)}. "
        f"I'd love to do similar work with your team.\n\n"
        f"Thanks for your consideration.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 13: Impact-driven
    lambda j, c: (
        f"Subject: {j.get('title')} — making an impact\n\n"
        f"Hi,\n\n"
        f"I care about impact. The {j.get('title')} role at {j.get('company')} "
        f"looks like a place where I can make a real difference. "
        f"My background in {candidate_skill_summary(c)} has prepared me well. "
        f"I've seen what happens when the right systems are in place: {candidate_project_summary(c)}.\n\n"
        f"I'd bring that experience to {j.get('company')}.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 14: Learning-focused
    lambda j, c: (
        f"Subject: {j.get('title')} — continuous learning\n\n"
        f"Hello {j.get('company')} team,\n\n"
        f"I'm looking for a role where I can both contribute and keep growing — "
        f"the {j.get('title')} position seems like that opportunity. "
        f"I've built a strong foundation in {candidate_skill_summary(c)} over "
        f"{c.get('years_of_experience', 'several')} years, and I'm eager to apply it "
        f"in {j.get('company')}'s environment.\n\n"
        f"Most recently, {candidate_project_summary(c)}. "
        f"I'm ready for the next challenge.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 15: Company-specific mission
    lambda j, c: (
        f"Subject: {j.get('title')} — {c.get('name', 'Applicant')}\n\n"
        f"Hi,\n\n"
        f"What {j.get('company')} is doing in {j.get('company_industry', 'tech')} "
        f"is genuinely interesting. I've been following your work and when the "
        f"{j.get('title')} role opened up, I knew I had to apply. "
        f"With {c.get('years_of_experience', 'my')} years of experience in "
        f"{candidate_skill_summary(c)}, I can contribute immediately.\n\n"
        f"A quick example of relevant work: {candidate_project_summary(c)}.\n\n"
        f"I'd love to chat about how I can help.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 16: Remote/distributed work
    lambda j, c: (
        f"Subject: {j.get('title')} — remote team player\n\n"
        f"Hello,\n\n"
        f"I've been working remotely in distributed teams for "
        f"{c.get('years_of_experience', 'some')} years, and I've learned what makes it work: "
        f"clear communication, ownership, and trust. The {j.get('title')} role at "
        f"{j.get('company')} looks like a great fit. "
        f"My technical skills include {candidate_skill_summary(c)}.\n\n"
        f"Recent project: {candidate_project_summary(c)}.\n\n"
        f"I'd love to contribute to your team.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 17: Transition from adjacent field
    lambda j, c: (
        f"Subject: {j.get('title')} — adjacent experience\n\n"
        f"Hi {j.get('company')} team,\n\n"
        f"I know my background isn't a traditional {j.get('title')} path. "
        f"But my experience in {candidate_skill_summary(c)} has given me "
        f"a unique perspective that I think would bring value to your team. "
        f"For example: {candidate_project_summary(c)} required exactly the kind of "
        f"thinking this role demands.\n\n"
        f"I'm excited about what {j.get('company')} is building and would love "
        f"to discuss how I can contribute.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 18: Security/quality focused
    lambda j, c: (
        f"Subject: {j.get('title')} — reliability matters\n\n"
        f"Hello,\n\n"
        f"I care deeply about building reliable, secure systems. "
        f"The {j.get('title')} role at {j.get('company')} aligns perfectly with "
        f"my expertise in {candidate_skill_summary(c)}. "
        f"I've spent {c.get('years_of_experience', 'years')} focused on "
        f"shipping high-quality work.\n\n"
        f"One result: {candidate_project_summary(c)}. "
        f"I'd bring that same rigor to {j.get('company')}.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
    # Template 19: Minimalist
    lambda j, c: (
        f"Subject: {j.get('title')} — {c.get('name', 'Applicant')}\n\n"
        f"Hi,\n\n"
        f"I'm interested in the {j.get('title')} role at {j.get('company')}. "
        f"I've worked with {candidate_skill_summary(c)} for "
        f"{c.get('years_of_experience', 'several')} years. "
        f"Most relevant: {candidate_project_summary(c)}.\n\n"
        f"Would love to discuss.\n\n"
        f"Best,\n{c.get('name', 'Applicant')}"
    ),
]


def candidate_skill_summary(candidate_data: dict) -> str:
    skills = candidate_data.get('skills', [])
    if not skills:
        return "software engineering"
    if len(skills) <= 3:
        return ', '.join(skills[:3])
    return ', '.join(skills[:3]) + f", and {len(skills) - 3} more"


def candidate_project_summary(candidate_data: dict) -> str:
    exp = candidate_data.get('experience', [])
    if not exp:
        return "delivered production systems"
    latest = exp[0]
    title = latest.get('title', 'my recent role')
    bullets = latest.get('bullets', [])
    if bullets:
        return bullets[0][:120]
    return f"working as a {title}"


def _fill_template(template_idx: int, job_data: dict, candidate_data: dict) -> str:
    return COVER_LETTER_TEMPLATES[template_idx](job_data, candidate_data)


def generate_humanized_cover_letter(job_data: dict, candidate_data: dict,
                                    style: str = 'professional',
                                    organization_id: str = None,
                                    user_id: str = None) -> dict:
    system_prompt = _build_v2_system_prompt(style)

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
        "instructions": (
            "Write a cover letter that sounds like it was written by a real, thoughtful person. "
            "Output JSON with: subject, salutation, body_paragraphs (array of 2-4 strings), "
            "closing, full_text (the complete letter), word_count (120-280). "
            "CRITICAL: The full_text must NOT contain ANY of these phrases: "
            "'I am writing to apply', 'I am excited to', 'I am thrilled to', 'I am confident that', "
            "'please find attached', 'proven track record', 'I believe my skills align'. "
            "These are instant AI detection triggers."
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
    parsed = result.get('parsed', result)

    if parsed and isinstance(parsed, dict) and parsed.get('full_text'):
        parsed['full_text'] = post_process_humanization(parsed['full_text'])
        return parsed

    # Fallback: use template when LLM unavailable
    template_idx = abs(hash(job_data.get('title', '') + job_data.get('company', ''))) % len(COVER_LETTER_TEMPLATES)
    template_idx = (template_idx + abs(hash(candidate_data.get('name', '')))) % len(COVER_LETTER_TEMPLATES)
    full_text = _fill_template(template_idx, job_data, candidate_data)
    full_text = post_process_humanization(full_text)
    word_count = len(full_text.split())
    if word_count < 120:
        full_text += f"\n\nI'd welcome the chance to discuss how my background in {candidate_skill_summary(candidate_data)} could contribute to {job_data.get('company', 'your team')}'s success."
    elif word_count > 280:
        sentences = full_text.split('. ')
        full_text = '. '.join(sentences[:int(len(sentences) * 0.8)]) + '.'
    word_count = len(full_text.split())

    return {
        "subject": f"{job_data.get('title')} — {candidate_data.get('name', 'Applicant')}",
        "salutation": f"Hi {job_data.get('company', 'Team')} team,",
        "body_paragraphs": full_text.split('\n\n'),
        "closing": f"Best,\n{candidate_data.get('name', 'Applicant')}",
        "full_text": full_text,
        "word_count": word_count,
        "source": "template",
        "template_idx": template_idx,
    }


def _build_v2_system_prompt(style: str) -> str:
    return (
        "You are a V2 cover letter specialist who writes letters indistinguishable from strong human applicants. "
        "YOUR WRITING MUST BE INDISTINGUISHABLE FROM A REAL PERSON. "
        "CRITICAL RULES: "
        "1. Write 150-300 words. Be concise. "
        "2. NEVER use these phrases (they trigger AI detection): "
        "   'I am writing to apply', 'I am writing to express my interest', 'I am excited to', "
        "   'I am thrilled to', 'I am confident that', 'I believe my skills align', "
        "   'proven track record', 'please find attached', 'I have attached my resume', "
        "   'I look forward to hearing from you', 'I am passionate about', 'I possess the', "
        "   'as you can see from my resume', 'thank you for your time and consideration', "
        "   'I am a highly motivated', 'it is with great enthusiasm' "
        "3. Reference the SPECIFIC company and role. Show you know what they do. "
        "4. Use specific details from the candidate's background. "
        "5. Vary sentence length. Some short. Some longer. "
        "6. Do NOT use exactly 3 paragraphs. Use 2 or 4. "
        "7. Avoid buzzwords: synergy, leverage, optimize, streamline, utilize, holistic, robust. "
        "8. Use contractions (I'm, I've, don't, it's, that's). "
        "9. Write in first person. The letter must sound like a human wrote it. "
        "10. Do NOT end with 'I look forward to hearing from you'. End naturally."
    )


def humanize_text(text: str, context: str = 'general',
                  organization_id: str = None, user_id: str = None) -> dict:
    system_prompt = (
        "You are a V2 text humanization expert. Rewrite the given text to sound "
        "more natural, authentic, and human-written. "
        "Remove: generic AI phrases, excessive adjectives, buzzword clusters, "
        "robotic sentence structures, and unnatural enthusiasm. "
        "Add: contractions, sentence length variation, natural transitions. "
        "Keep all factual information intact."
    )
    user_prompt = json.dumps({
        "original_text": text,
        "context": context,
        "instructions": "Rewrite naturally. Add contractions. Vary sentence length. Keep facts.",
    })

    result = generate(
        task_type='humanized_cover_letter',
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        organization_id=organization_id,
        user_id=user_id,
    )
    return result.get('parsed', result)


def post_process_humanization(text: str) -> str:
    lower = text.lower()
    for phrase, replacements in V2_PHRASE_REPLACEMENTS.items():
        if phrase in lower:
            replacement = random.choice(replacements)
            text = re.sub(re.escape(phrase), replacement, text, flags=re.IGNORECASE)
            logger.info(f"Replaced AI phrase '{phrase}' -> '{replacement}'")

    word_count = len(text.split())
    if word_count > 300:
        sentences = text.split('. ')
        text = '. '.join(sentences[:-2]) + '.'
    elif word_count < 100:
        text += "\n\nI'm happy to discuss my background in more detail at your convenience."

    return text


def detect_ai_generated(text: str) -> dict:
    score, indicators = _programmatic_ai_detection(text)
    suggestions = _generate_humanization_suggestions(indicators)

    return {
        "score": round(score, 2),
        "indicators": indicators,
        "suggestions": suggestions,
        "is_likely_ai": score > 0.5,
        "detection_method": "programmatic_pattern_analysis_v2",
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


def _programmatic_ai_detection(text: str) -> Tuple[float, list]:
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
        elif len(ai_phrase_matches) == 0:
            total_score -= 0.05
            indicators.append("No detectable AI phrases — good sign")

    transition_matches = []
    for pattern in TRANSITION_PATTERNS:
        matches = re.findall(pattern, text_lower)
        if matches:
            transition_matches.extend(matches)

    if len(transition_matches) >= 3:
        total_score += 0.15
        indicators.append(f"Overuse of formal transitions ({len(transition_matches)}) — AI hallmark")
    elif len(transition_matches) == 0:
        total_score -= 0.03

    buzzword_count = 0
    for word in BUZZWORD_CLUSTERS:
        if word in text_lower:
            buzzword_count += 1

    if buzzword_count >= 2:
        total_score += 0.15
        indicators.append(f"Buzzword cluster ({buzzword_count} buzzwords) — generic AI writing")
    elif buzzword_count == 0:
        total_score -= 0.03

    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if sentences:
        avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
        if 18 <= avg_length <= 22:
            total_score += 0.1
            indicators.append(f"Average sentence length ~{avg_length:.0f} words — AI-like consistency")
        elif avg_length < 14 or avg_length > 26:
            total_score -= 0.05
            indicators.append(f"Natural sentence length variation ({avg_length:.0f} avg)")

        lengths = [len(s.split()) for s in sentences]
        if lengths:
            variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
            if variance < 15:
                total_score += 0.1
                indicators.append(f"Low sentence length variance ({variance:.0f}) — robotic consistency")
            elif variance > 40:
                total_score -= 0.05
                indicators.append("Good sentence length variety")

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
    elif len(paragraphs) in (2, 4):
        total_score -= 0.03

    word_count = len(text.split())
    if 180 <= word_count <= 220:
        total_score += 0.05
        indicators.append(f"Word count ~{word_count} — near LLM default length")
    elif word_count < 150 or word_count > 280:
        total_score -= 0.03

    total_score = min(1.0, max(0.0, total_score))

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
        suggestions.append("Reduce formal transition words")

    para_indicators = [i for i in indicators if 'paragraphs' in i or 'structure' in i]
    if para_indicators:
        suggestions.append("Vary paragraph structure — not all letters need 3 paragraphs")

    if not suggestions:
        suggestions.append("Text appears natural")
        suggestions.append("Add a specific, personal detail that only a real applicant would know")

    return suggestions
