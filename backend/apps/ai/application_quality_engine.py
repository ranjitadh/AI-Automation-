import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def _score_resume_quality(resume_data: dict) -> int:
    score = 60
    if not resume_data:
        return 0
    exp_count = len(resume_data.get("experience", []))
    if exp_count >= 5:
        score += 15
    elif exp_count >= 3:
        score += 10
    elif exp_count >= 1:
        score += 5
    skills_count = len(resume_data.get("skills", []))
    if skills_count >= 15:
        score += 10
    elif skills_count >= 8:
        score += 5
    summary = resume_data.get("summary", "")
    if summary and len(summary.split()) >= 40:
        score += 5
    education = resume_data.get("education", [])
    if education:
        score += 5
    projects = resume_data.get("projects", [])
    if projects:
        score += 5
    return min(100, max(0, score))


def _score_cover_letter_quality(cover_letter_text: str) -> int:
    if not cover_letter_text or len(cover_letter_text.strip()) < 50:
        return 0
    score = 60
    wc = len(cover_letter_text.split())
    if 120 <= wc <= 280:
        score += 15
    elif wc < 80 or wc > 400:
        score -= 10
    lower = cover_letter_text.lower()
    company_mentioned = bool(re.search(r'(?i)\b(company|inc|corp|llc|ltd)\b', lower))
    role_mentioned = bool(re.search(r'(?i)\b(position|role|opportunity)\b', lower))
    if company_mentioned or role_mentioned:
        score += 10
    first_person = sum(1 for p in ["i've", "i'm", "i'd", "i'll", "my"] if p in lower)
    if first_person >= 3:
        score += 10
    paragraphs = [p.strip() for p in cover_letter_text.split("\n\n") if p.strip()]
    if 2 <= len(paragraphs) <= 5:
        score += 5
    return min(100, max(0, score))


SALARY_BANDS = {
    "entry": {"min": 50000, "max": 90000, "label": "Entry"},
    "junior": {"min": 60000, "max": 110000, "label": "Junior"},
    "mid": {"min": 90000, "max": 160000, "label": "Mid"},
    "senior": {"min": 130000, "max": 220000, "label": "Senior"},
    "lead": {"min": 160000, "max": 260000, "label": "Lead"},
    "principal": {"min": 190000, "max": 320000, "label": "Principal"},
    "staff": {"min": 180000, "max": 300000, "label": "Staff"},
    "manager": {"min": 140000, "max": 240000, "label": "Manager"},
    "director": {"min": 180000, "max": 350000, "label": "Director"},
    "vp": {"min": 250000, "max": 500000, "label": "VP"},
    "head": {"min": 250000, "max": 500000, "label": "Head"},
}


def _infer_seniority(job_data: dict, resume_data: dict) -> str:
    title = ((job_data or {}).get("title") or "").lower()
    for level, info in SALARY_BANDS.items():
        if level in title:
            return level
    cand_seniority = ((resume_data or {}).get("seniority_level") or "").lower()
    if cand_seniority in SALARY_BANDS:
        return cand_seniority
    years = (resume_data or {}).get("years_of_experience", 0) or 0
    if years < 2:
        return "entry"
    elif years < 4:
        return "junior"
    elif years < 7:
        return "mid"
    elif years < 10:
        return "senior"
    elif years < 15:
        return "lead"
    return "principal"


def _get_salary_band(job_data: dict, resume_data: dict) -> dict:
    seniority = _infer_seniority(job_data, resume_data)
    return SALARY_BANDS.get(seniority, SALARY_BANDS["mid"])


def assess_compensation_fit(profile_data: dict, job_data: dict, resume_data: dict) -> dict:
    if not job_data:
        return {"score": 50, "risk": "unknown", "reasons": ["No job data"]}
    score = 70
    reasons = []
    risk = "none"
    goals = profile_data.get("goals", {}) if profile_data else {}
    target_min = goals.get("target_salary_min") or profile_data.get("target_salary_min")
    target_max = goals.get("target_salary_max") or profile_data.get("target_salary_max")
    job_min = job_data.get("salary_min") or 0
    job_max = job_data.get("salary_max") or 0
    band = _get_salary_band(job_data, resume_data)
    band_mid = (band["min"] + band["max"]) // 2 if band else 125000
    market_range = (band["min"], band["max"])
    reasons.append(f"Market band for level: ${market_range[0]:,}-${market_range[1]:,}")

    # Check if job salary is below market
    if job_max and job_max < market_range[0] * 0.8:
        score -= 15
        risk = "high"
        reasons.append(f"Job max ${job_max:,} is well below market ${market_range[0]:,}")
    elif job_max and job_max < market_range[0]:
        score -= 8
        if risk == "none":
            risk = "medium"
        reasons.append(f"Job max ${job_max:,} below market floor ${market_range[0]:,}")

    # Check if candidate is overpricing (expecting > 1.3x job max)
    if target_min and job_max and target_min > job_max * 1.3:
        score -= 12
        if risk == "none":
            risk = "medium"
        reasons.append(f"Candidate min ${target_min:,} far exceeds job max ${job_max:,}")

    # Check if candidate is underpricing (expecting < 0.7x job max or < 0.6x market)
    if target_max and job_max and target_max < job_max * 0.7:
        score -= 8
        risk = "high"
        reasons.append(f"Candidate max ${target_max:,} is well below job max ${job_max:,} — underpricing risk")
    elif target_max and band_mid and target_max < band_mid * 0.6:
        score -= 5
        reasons.append(f"Candidate max ${target_max:,} is below market — may signal desperation")

    # Good alignment bonus
    if target_min and job_min and target_max and job_max:
        overlap_min = max(target_min, job_min)
        overlap_max = min(target_max, job_max)
        if overlap_max >= overlap_min:
            score += 10
            reasons.append(f"Salary overlap: ${overlap_min:,}-${overlap_max:,}")
            risk = "none"

    score = max(0, min(100, score))
    return {
        "score": score,
        "risk": risk,
        "reasons": reasons,
        "market_band": market_range,
        "job_range": (job_min, job_max) if job_min or job_max else None,
        "candidate_range": (target_min, target_max) if target_min or target_max else None,
    }


def evaluate_application_quality(
    resume_data: dict,
    cover_letter_text: str,
    screening_answers: list,
    profile_data: dict,
    job_data: dict,
) -> dict:
    quality_score, quality_factors = _score_application_quality(
        resume_data, cover_letter_text, screening_answers, profile_data, job_data
    )
    authenticity_score, auth_factors = _score_authenticity(
        resume_data, cover_letter_text, screening_answers, profile_data
    )
    humanity_score, humanity_factors = _score_humanity(cover_letter_text)
    ai_detection_risk = _assess_ai_detection_risk(
        resume_data, cover_letter_text, screening_answers
    )
    overqual_risk = _assess_overqualification_risk(resume_data, job_data)
    underqual_risk = _assess_underqualification_risk(resume_data, job_data)

    # Compensation fit scoring
    comp_fit = assess_compensation_fit(profile_data, job_data, resume_data)

    # ── COMPOSITE QUALITY SCORE (SIMPLIFIED) ─────────────────
    resume_quality = _score_resume_quality(resume_data)
    cover_letter_quality = _score_cover_letter_quality(cover_letter_text)
    comp_score = comp_fit["score"]
    ai_score = 100 - ai_detection_risk.get("risk_percentage", 0)
    over_penalty = max(0, 100 - overqual_risk.get("severity", 0) * 12)
    under_penalty = max(0, 100 - underqual_risk.get("severity", 0) * 12)

    composite_score = int(
        quality_score * 0.20 +
        authenticity_score * 0.10 +
        humanity_score * 0.10 +
        resume_quality * 0.15 +
        cover_letter_quality * 0.10 +
        comp_score * 0.10 +
        ai_score * 0.10 +
        over_penalty * 0.075 +
        under_penalty * 0.075
    )
    composite_score = max(0, min(100, composite_score))
    # ──────────────────────────────────────────────────────────

    submission_confidence = _compute_submission_confidence(
        quality_score, authenticity_score, humanity_score, ai_detection_risk,
        overqual_risk, underqual_risk
    )

    return {
        "application_quality_score": quality_score,
        "application_authenticity_score": authenticity_score,
        "humanity_score": humanity_score,
        "composite_quality_score": composite_score,
        "resume_quality_score": resume_quality,
        "cover_letter_quality_score": cover_letter_quality,
        "compensation_fit": comp_fit,
        "ai_detection_risk": ai_detection_risk,
        "overqualification_risk": overqual_risk,
        "underqualification_risk": underqual_risk,
        "submission_confidence": submission_confidence,
        "quality_factors": quality_factors,
        "authenticity_factors": auth_factors,
        "humanity_factors": humanity_factors,
        "should_submit": submission_confidence >= 0.5 and ai_detection_risk["level"] in ["none", "low"],
        "can_auto_submit": composite_score >= 85 and submission_confidence >= 0.7 and ai_detection_risk["level"] == "none" and comp_fit["risk"] != "high",
        "auto_submit_blocked": composite_score < 85 or comp_fit["risk"] == "high",
        "compensation_risk": comp_fit["risk"],
    }


def _score_application_quality(
    resume_data: dict, cover_letter_text: str,
    screening_answers: list, profile_data: dict, job_data: dict,
) -> tuple:
    score = 70
    factors = []

    if resume_data:
        exp_count = len(resume_data.get("experience", []))
        skills_count = len(resume_data.get("skills", []))
        if exp_count >= 3 and skills_count >= 10:
            score += 10
            factors.append("Strong resume depth")
        elif exp_count >= 1 and skills_count >= 5:
            score += 5
            factors.append("Adequate resume content")
        elif exp_count == 0:
            score -= 20
            factors.append("No experience listed")

        summary = resume_data.get("summary", "")
        if summary and len(summary.split()) >= 30:
            score += 3
            factors.append("Detailed professional summary")

    if cover_letter_text:
        words = cover_letter_text.split()
        if 120 <= len(words) <= 280:
            score += 5
            factors.append("Optimal cover letter length")
        elif len(words) > 400:
            score -= 5
            factors.append("Cover letter too verbose")

        company_name = job_data.get("company_name", "")
        if company_name and company_name.lower() in cover_letter_text.lower():
            score += 5
            factors.append("Personalized to company")
        role_title = job_data.get("title", "")
        if role_title and role_title.lower() in cover_letter_text.lower():
            score += 3
            factors.append("Personalized to role")
    else:
        score -= 10
        factors.append("No cover letter")

    if screening_answers:
        avg_conf = sum(a.get("confidence", 1.0) for a in screening_answers if isinstance(a, dict))
        avg_conf /= len(screening_answers)
        if avg_conf >= 0.8:
            score += 5
            factors.append("High-confidence screening answers")
        elif avg_conf < 0.4:
            score -= 5
            factors.append("Low-confidence screening answers")

    profile_skills = profile_data.get("skills", [])
    if profile_skills:
        score += min(len(profile_skills), 5)
        factors.append(f"{len(profile_skills)} skills in profile")

    score = max(0, min(100, score))
    return score, factors


def _score_authenticity(
    resume_data: dict, cover_letter_text: str,
    screening_answers: list, profile_data: dict,
) -> tuple:
    score = 80
    factors = []

    exp_count = len(resume_data.get("experience", []))
    if exp_count >= 2:
        for exp in resume_data.get("experience", []):
            bullets = exp.get("bullets", []) or []
            for b in bullets:
                if len(b.split()) > 40:
                    score -= 1
                    factors.append("Overly verbose bullet points")

    if cover_letter_text:
        lower = cover_letter_text.lower()
        generic_openings = [
            "i am writing to apply", "i am writing to express",
            "i am excited to apply", "i am interested in",
            "please accept this letter", "i am submitting my application",
        ]
        for phrase in generic_openings:
            if phrase in lower:
                score -= 5
                factors.append(f"Generic opening: '{phrase}'")
                break

        if "i am confident that my" in lower or "i believe that my" in lower:
            score -= 3
            factors.append("Generic confidence statement")

        exclamation_count = cover_letter_text.count("!")
        if exclamation_count > 3:
            score -= 3
            factors.append("Excessive exclamation marks")
    else:
        score -= 15
        factors.append("No cover letter")

    profile_skills = set(s.lower() for s in profile_data.get("skills", []))
    resume_skills = set(s.lower() for s in resume_data.get("skills", []))
    if profile_skills and resume_skills:
        overlap = len(profile_skills & resume_skills)
        total = max(len(profile_skills), len(resume_skills))
        if total > 0 and overlap / total < 0.5:
            score -= 5
            factors.append("Resume skills differ from profile skills")

    if screening_answers:
        contradictions = sum(
            1 for a in screening_answers if isinstance(a, dict) and not a.get("consistent_with_resume", True)
        )
        if contradictions > 0:
            score -= contradictions * 5
            factors.append(f"{contradictions} answer(s) contradict resume")

    score = max(0, min(100, score))
    return score, factors


def _score_humanity(cover_letter_text: str) -> tuple:
    score = 50
    factors = []

    if not cover_letter_text:
        return 30, ["No cover letter to evaluate"]

    words = cover_letter_text.split()
    word_count = len(words)

    if 100 <= word_count <= 300:
        score += 10
        factors.append("Natural length")
    elif word_count > 500:
        score -= 10
        factors.append("Too long for human applicant")
    elif word_count < 50:
        score -= 15
        factors.append("Too short")

    lower = cover_letter_text.lower()
    ai_phrase_score = 0
    for phrase in _AI_PHRASES:
        if phrase in lower:
            ai_phrase_score += 1
    if ai_phrase_score >= 4:
        score -= 15
        factors.append(f"Multiple AI phrases detected ({ai_phrase_score})")
    elif ai_phrase_score >= 2:
        score -= 5
        factors.append(f"Some AI-like phrases ({ai_phrase_score})")
    else:
        score += 5
        factors.append("No detectable AI phrasing")

    buzzwords = ["synergy", "leverage", "optimize", "innovative", "dynamic",
                 "strategic", "utilize", "streamline", "proactive", "results-driven"]
    buzz_count = sum(1 for b in buzzwords if b in lower)
    if buzz_count >= 3:
        score -= 10
        factors.append("Buzzword-heavy")
    elif buzz_count >= 1:
        score -= 2
    else:
        score += 3
        factors.append("Buzzword-free")

    sentences = re.split(r'[.!?]+', cover_letter_text)
    valid_sentences = [s.strip() for s in sentences if len(s.strip().split()) > 2]
    if len(valid_sentences) >= 3:
        lengths = [len(s.split()) for s in valid_sentences]
        avg_len = sum(lengths) / len(lengths)
        variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths) if lengths else 0
        if variance < 10:
            score -= 8
            factors.append("Uniform sentence length (robotic pattern)")
        elif variance > 50:
            score += 5
            factors.append("Natural sentence length variation")

    score = max(0, min(100, score))
    return score, factors


def _assess_ai_detection_risk(resume_data: dict, cover_letter_text: str, screening_answers: list) -> dict:
    indicators = []
    severity = 0

    if cover_letter_text:
        lower = cover_letter_text.lower()
        ai_hits = sum(1 for p in _AI_PHRASES if p in lower)
        if ai_hits >= 4:
            severity += 3
            indicators.append(f"AI phrases ({ai_hits})")
        elif ai_hits >= 2:
            severity += 1
            indicators.append(f"Suspicious phrases ({ai_hits})")

        words = cover_letter_text.split()
        if 180 <= len(words) <= 220:
            severity += 2
            indicators.append("LLM-default word count")
        elif 140 <= len(words) <= 250:
            severity += 1
            indicators.append("Near LLM-default length")

        sentences = re.split(r'[.!?]+', cover_letter_text)
        valid = [s.strip() for s in sentences if len(s.strip().split()) > 3]
        if len(valid) >= 3:
            lengths = [len(s.split()) for s in valid]
            avg_len = sum(lengths) / len(lengths)
            variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths) if lengths else 0
            if variance < 10:
                severity += 2
                indicators.append("Uniform sentence length")

        transitions = ["however", "furthermore", "moreover", "additionally", "consequently",
                       "nevertheless", "subsequently", "accordingly"]
        if sum(1 for t in transitions if t in lower) >= 3:
            severity += 1
            indicators.append("Overused formal transitions")

        paragraphs = [p.strip() for p in cover_letter_text.split("\n\n") if p.strip()]
        if len(paragraphs) == 3:
            severity += 1
            indicators.append("Exactly 3 paragraphs (LLM default)")

        if cover_letter_text.count("!") > 3:
            severity += 1
            indicators.append("Excessive exclamation marks")

    cliche_bullets = 0
    for exp in resume_data.get("experience", []):
        for bullet in exp.get("bullets", []):
            lower_b = bullet.lower()
            if any(c in lower_b for c in ["responsible for", "duties included", "tasked with"]):
                cliche_bullets += 1
    if cliche_bullets >= 3:
        severity += 1
        indicators.append("Cliche resume bullets")

    if severity >= 6:
        level = "high"
    elif severity >= 3:
        level = "medium"
    elif severity >= 1:
        level = "low"
    else:
        level = "none"

    risk_pct = min(severity * 12, 95)

    return {
        "level": level,
        "risk_percentage": risk_pct,
        "indicators": indicators,
        "severity": severity,
    }


def _assess_overqualification_risk(resume_data: dict, job_data: dict) -> dict:
    risk = "none"
    reasons = []
    severity = 0

    job_years = job_data.get("years_experience_required", 0) or job_data.get("years_required", 0)
    cand_years = resume_data.get("years_of_experience", 0)
    if not cand_years:
        total_months = 0
        for exp in resume_data.get("experience", []):
            start = exp.get("start_date", "")
            end = exp.get("end_date", "") or ""
            if not start:
                continue
            try:
                parts = start.split("-")
                sy = int(parts[0])
                sm = int(parts[1]) if len(parts) > 1 else 1
                if end.lower() == "present":
                    import datetime
                    ey, em = datetime.datetime.now().year, datetime.datetime.now().month
                elif end:
                    parts = end.split("-")
                    ey = int(parts[0])
                    em = int(parts[1]) if len(parts) > 1 else 1
                else:
                    continue
                total_months += (ey - sy) * 12 + (em - sm)
            except (ValueError, IndexError):
                continue
        cand_years = total_months // 12

    if job_years and cand_years:
        ratio = cand_years / job_years if job_years > 0 else 0
        if ratio >= 3:
            risk = "high"
            severity = 3
            reasons.append(f"{cand_years} years for a role requiring {job_years}")
        elif ratio >= 2:
            risk = "medium"
            severity = 2
            reasons.append(f"{cand_years} years vs {job_years} required")
        elif ratio >= 1.5:
            risk = "low"
            severity = 1
            reasons.append(f"Slightly overqualified ({cand_years} vs {job_years})")

    job_seniority = (job_data.get("seniority_level") or job_data.get("title", "")).lower()
    cand_seniority = (resume_data.get("seniority_level") or "").lower()
    seniority_map = {"junior": 1, "mid": 2, "senior": 3, "lead": 4, "principal": 5, "staff": 5, "manager": 4, "director": 6, "vp": 7, "head": 7}
    job_s = seniority_map.get(job_seniority, 0)
    cand_s = seniority_map.get(cand_seniority, 0)
    if cand_s - job_s >= 3:
        severity += 2
        reasons.append(f"Candidate seniority ({cand_seniority}) far exceeds role ({job_seniority})")
        if risk == "none":
            risk = "medium"

    return {"risk": risk, "severity": severity, "reasons": reasons, "years_of_experience": cand_years}


def _assess_underqualification_risk(resume_data: dict, job_data: dict) -> dict:
    risk = "none"
    reasons = []
    severity = 0

    job_skills = set(s.lower() for s in job_data.get("required_skills", []))
    resume_skills = set(s.lower() for s in resume_data.get("skills", []))
    if job_skills:
        missing = job_skills - resume_skills
        missing_pct = len(missing) / len(job_skills) if job_skills else 0
        if missing_pct > 0.5:
            severity += 3
            risk = "high"
            reasons.append(f"Missing {len(missing)}/{len(job_skills)} required skills")
        elif missing_pct > 0.3:
            severity += 2
            risk = "medium" if risk == "none" else risk
            reasons.append(f"Missing {len(missing)}/{len(job_skills)} required skills")
        elif missing_pct > 0.15:
            severity += 1
            risk = "low" if risk == "none" else risk
            reasons.append(f"Missing {len(missing)}/{len(job_skills)} skills")

    job_years = job_data.get("years_experience_required", 0) or job_data.get("years_required", 0)
    cand_years = resume_data.get("years_of_experience", 0)
    if not cand_years:
        cand_years = 0
    if job_years and cand_years < job_years * 0.6:
        severity += 2
        reasons.append(f"Only {cand_years} years vs {job_years} required")
        if risk == "none":
            risk = "medium"

    return {"risk": risk, "severity": severity, "reasons": reasons}


def _compute_submission_confidence(
    quality: int, authenticity: int, humanity: int,
    ai_risk: dict, overqual: dict, underqual: dict,
) -> float:
    base = (quality + authenticity + humanity) / 300.0

    ai_penalty = 0.0
    if ai_risk["level"] == "high":
        ai_penalty = 0.25
    elif ai_risk["level"] == "medium":
        ai_penalty = 0.10
    elif ai_risk["level"] == "low":
        ai_penalty = 0.03

    over_penalty = overqual["severity"] * 0.04
    under_penalty = underqual["severity"] * 0.05

    confidence = base - ai_penalty - over_penalty - under_penalty
    return round(max(0.0, min(1.0, confidence)), 2)


_AI_PHRASES = [
    "i am writing to apply", "i am writing to express", "i am excited to",
    "i am thrilled to", "i would be honored", "it is with great enthusiasm",
    "proven track record", "i am confident that my", "i possess the",
    "i am eager to", "please find attached", "i have attached",
    "as you can see from my", "i believe that my skills",
    "i am a highly motivated", "i am writing this letter",
    "thank you for your time and consideration", "i look forward to hearing from you",
    "i am interested in", "i am passionate about", "i am writing to express my interest",
    "i am submitting my application", "please accept this letter",
    "my background includes", "i bring a unique combination",
]
