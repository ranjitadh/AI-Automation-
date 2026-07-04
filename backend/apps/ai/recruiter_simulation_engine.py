import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def simulate_recruiter_perspectives(
    resume_data: dict,
    cover_letter_text: str,
    screening_answers: list,
    profile_data: dict,
    job_data: dict,
) -> dict:
    hr_score, hr_reasoning = _simulate_hr_recruiter(resume_data, cover_letter_text, profile_data)
    hm_score, hm_reasoning = _simulate_hiring_manager(resume_data, job_data, screening_answers)
    ats_result = _simulate_ats(resume_data, job_data)
    ti_score, ti_reasoning = _simulate_technical_interviewer(resume_data, job_data)

    # ── FIX #6: RECRUITER SIMULATION V2 ──────────────────────
    pf_score, pf_reasoning = _evaluate_portfolio_quality(resume_data)
    gh_score, gh_reasoning = _evaluate_github_presence(resume_data)
    pr_score, pr_reasoning = _evaluate_project_relevance(resume_data, job_data)
    cf_score, cf_reasoning = _evaluate_cultural_fit(resume_data, job_data, cover_letter_text)
    cq_score, cq_reasoning = _evaluate_communication_quality(cover_letter_text)
    # ──────────────────────────────────────────────────────────

    combined = _combine_scores(hr_score, hm_score, ats_result["ats_score"], ti_score)

    return {
        "interview_probability": combined["interview_probability"],
        "rejection_probability": combined["rejection_probability"],
        "ats_probability": ats_result["ats_score"] / 100.0,
        "hiring_manager_score": hm_score,
        "recruiter_score": hr_score,
        "technical_interviewer_score": ti_score,
        "portfolio_quality_score": pf_score,
        "github_presence_score": gh_score,
        "project_relevance_score": pr_score,
        "cultural_fit_score": cf_score,
        "communication_quality_score": cq_score,
        "confidence_score": combined["confidence"],
        "perspectives": {
            "hr_recruiter": {
                "score": hr_score,
                "reasoning": hr_reasoning,
                "red_flags": _hr_red_flags(resume_data, cover_letter_text),
            },
            "hiring_manager": {
                "score": hm_score,
                "reasoning": hm_reasoning,
                "strengths": _hm_strengths(resume_data, job_data),
                "concerns": _hm_concerns(resume_data, job_data),
            },
            "ats": {
                "score": ats_result["ats_score"],
                "keyword_match": ats_result["keyword_match"],
                "formatting_issues": ats_result["formatting_issues"],
                "missing_sections": ats_result["missing_sections"],
            },
            "technical_interviewer": {
                "score": ti_score,
                "reasoning": ti_reasoning,
                "skill_gaps": _tech_skill_gaps(resume_data, job_data),
            },
            "portfolio_quality": {
                "score": pf_score,
                "reasoning": pf_reasoning,
            },
            "github_presence": {
                "score": gh_score,
                "reasoning": gh_reasoning,
            },
            "project_relevance": {
                "score": pr_score,
                "reasoning": pr_reasoning,
            },
            "cultural_fit": {
                "score": cf_score,
                "reasoning": cf_reasoning,
            },
            "communication_quality": {
                "score": cq_score,
                "reasoning": cq_reasoning,
            },
        },
        "combined": combined,
    }


def _count_relevant_experience(resume_data: dict, job_data: dict) -> int:
    count = 0
    job_skills = set(s.lower() for s in job_data.get("required_skills", []))
    for exp in resume_data.get("experience", []):
        title = (exp.get("title", "") or "").lower()
        bullets = " ".join(exp.get("bullets", []) or []).lower()
        combined = title + " " + bullets
        if any(s in combined for s in job_skills):
            count += 1
    return count


def _simulate_hr_recruiter(resume_data: dict, cover_letter_text: str, profile_data: dict) -> tuple:
    score = 70
    reasons = []

    if not resume_data:
        return 0, ["No resume provided"]

    years = resume_data.get("years_of_experience", 0) or _compute_experience_years(resume_data)
    if years >= 10:
        score += 5
        reasons.append("Strong experience depth")
    elif years >= 5:
        score += 3
        reasons.append("Adequate experience")
    elif years < 2:
        score -= 15
        reasons.append("Limited experience")

    if cover_letter_text:
        cl_words = len(cover_letter_text.split())
        if 100 <= cl_words <= 350:
            score += 5
            reasons.append("Cover letter appropriate length")
        elif cl_words > 500:
            score -= 5
            reasons.append("Cover letter too long")
        elif cl_words < 50:
            score -= 10
            reasons.append("Cover letter too short")

        if _has_proper_salutation_closing(cover_letter_text):
            score += 3
            reasons.append("Proper cover letter format")

    profile_skills = profile_data.get("skills", resume_data.get("skills", []))
    if len(profile_skills) >= 8:
        score += 3
        reasons.append("Well-rounded skill set")
    elif len(profile_skills) < 3:
        score -= 5
        reasons.append("Very limited skills listed")

    target_titles = profile_data.get("target_titles", [])
    if target_titles and any(t in str(resume_data.get("target_titles", "")) or
                              any(kw in t.lower() for kw in ["engineer", "developer", "architect", "manager"])
                              for t in (target_titles if isinstance(target_titles, list) else [target_titles])):
        score += 2
        reasons.append("Career trajectory alignment")

    score = max(0, min(100, score))
    return score, "; ".join(reasons) if reasons else "No standout factors"


def _simulate_hiring_manager(resume_data: dict, job_data: dict, screening_answers: list) -> tuple:
    score = 65
    reasons = []

    job_skills = set(s.lower() for s in job_data.get("required_skills", []))
    resume_skills = set(s.lower() for s in resume_data.get("skills", []))

    if job_skills and resume_skills:
        overlap = len(job_skills & resume_skills)
        total = len(job_skills)
        if total > 0:
            pct = overlap / total
            if pct >= 0.8:
                score += 15
                reasons.append(f"Strong skill match ({overlap}/{total})")
            elif pct >= 0.6:
                score += 10
                reasons.append(f"Good skill match ({overlap}/{total})")
            elif pct >= 0.4:
                score += 5
                reasons.append(f"Partial skill match ({overlap}/{total})")
            else:
                score -= 10
                reasons.append(f"Weak skill match ({overlap}/{total})")

    job_years_req = job_data.get("years_experience_required", 0) or job_data.get("years_required", 0)
    candidate_years = resume_data.get("years_of_experience", 0) or _compute_experience_years(resume_data)
    if job_years_req and candidate_years:
        if candidate_years >= job_years_req * 1.5:
            score -= 8
            reasons.append("Potentially overqualified")
        elif candidate_years >= job_years_req:
            score += 8
            reasons.append("Experience level matches requirements")
        elif candidate_years >= job_years_req * 0.7:
            score += 3
            reasons.append("Close to experience requirement")
        else:
            score -= 12
            reasons.append("Below experience requirement")

    if screening_answers:
        for ans in screening_answers:
            if isinstance(ans, dict):
                conf = ans.get("confidence", 1.0)
                if conf < 0.3:
                    score -= 5
                    reasons.append(f"Low confidence answer: {ans.get('question', '')[:50]}")
                    break

    relevant_exp = _count_relevant_experience(resume_data, job_data)
    if relevant_exp > 0:
        score += min(relevant_exp * 3, 10)
        reasons.append(f"{relevant_exp} relevant experience entries")

    score = max(0, min(100, score))
    return score, "; ".join(reasons) if reasons else "Adequate candidate"


def _simulate_ats(resume_data: dict, job_data: dict) -> dict:
    score = 70
    keyword_match = 0.0
    formatting_issues = []
    missing_sections = []

    job_skills = set(s.lower() for s in job_data.get("required_skills", []))
    resume_text = " ".join([
        resume_data.get("summary", "") or "",
        " ".join(s.lower() for s in resume_data.get("skills", [])),
        " ".join(
            e.get("bullets", [])[0] if isinstance(e.get("bullets"), list) and e.get("bullets") else ""
            for e in resume_data.get("experience", [])
        ),
    ]).lower()

    if job_skills:
        matched = sum(1 for s in job_skills if s in resume_text)
        keyword_match = matched / len(job_skills) if job_skills else 0
        score += int(keyword_match * 20) - 10

    if not resume_data.get("summary"):
        missing_sections.append("Professional summary")
        score -= 5

    if not resume_data.get("skills"):
        missing_sections.append("Skills section")
        score -= 8

    if not resume_data.get("experience"):
        missing_sections.append("Experience section")
        score -= 15

    exp_count = len(resume_data.get("experience", []))
    if exp_count < 1:
        missing_sections.append("Work history")
        score -= 10

    score = max(0, min(100, score))
    return {
        "ats_score": score,
        "keyword_match": round(keyword_match, 2),
        "formatting_issues": formatting_issues,
        "missing_sections": missing_sections,
    }


def _simulate_technical_interviewer(resume_data: dict, job_data: dict) -> tuple:
    score = 65
    reasons = []

    job_tech = set(
        t.lower() for t in (
            job_data.get("required_skills", []) +
            job_data.get("technologies", []) +
            job_data.get("tools", [])
        )
    )
    resume_tech = set(
        s.lower() for s in (
            resume_data.get("skills", []) +
            resume_data.get("technologies", [])
        )
    )

    if job_tech and resume_tech:
        overlap = len(job_tech & resume_tech)
        total = len(job_tech)
        if total > 0:
            pct = overlap / total
            if pct >= 0.7:
                score += 15
                reasons.append(f"Strong technical alignment ({overlap}/{total})")
            elif pct >= 0.4:
                score += 5
                reasons.append(f"Partial technical alignment ({overlap}/{total})")
            else:
                score -= 10
                reasons.append(f"Poor technical alignment ({overlap}/{total})")
            score += min(overlap * 2, 10)

    for exp in resume_data.get("experience", []):
        title = (exp.get("title", "") or "").lower()
        bullets = " ".join(exp.get("bullets", []) or []).lower()
        if any(tech in title or tech in bullets for tech in job_tech):
            score += 2

    if not job_tech:
        score += 5
        reasons.append("No specific tech requirements to evaluate")

    score = max(0, min(100, score))
    return score, "; ".join(reasons) if reasons else "Adequate technical fit"


def _combine_scores(hr: int, hm: int, ats: int, ti: int) -> dict:
    weights = {"hr": 0.20, "hm": 0.35, "ats": 0.20, "ti": 0.25}
    weighted = hr * weights["hr"] + hm * weights["hm"] + ats * weights["ats"] + ti * weights["ti"]

    spread = max(hr, hm, ats, ti) - min(hr, hm, ats, ti)
    confidence = max(0.0, 1.0 - (spread / 200.0))

    interview_prob = weighted / 100.0
    rejection_prob = 1.0 - interview_prob

    return {
        "weighted_score": round(weighted, 1),
        "interview_probability": round(interview_prob, 2),
        "rejection_probability": round(rejection_prob, 2),
        "confidence": round(confidence, 2),
    }


def _hr_red_flags(resume_data: dict, cover_letter_text: str) -> list:
    flags = []
    if resume_data.get("employment_gaps", 0) and resume_data.get("employment_gaps", 0) > 12:
        flags.append("Employment gap over 12 months")
    if len(cover_letter_text.split()) > 500:
        flags.append("Excessively long cover letter")
    if _looks_ai_generated(cover_letter_text):
        flags.append("Cover letter appears AI-generated")
    recent = [e for e in resume_data.get("experience", []) if _is_recent(e)]
    if len(recent) < 2 and len(resume_data.get("experience", [])) >= 2:
        flags.append("Multiple short tenures at recent positions")
    return flags


def _hm_strengths(resume_data: dict, job_data: dict) -> list:
    strengths = []
    job_skills = set(s.lower() for s in job_data.get("required_skills", []))
    resume_skills = set(s.lower() for s in resume_data.get("skills", []))
    matched = job_skills & resume_skills
    if matched:
        strengths.append(f"Direct experience with: {', '.join(list(matched)[:5])}")
    exp_count = len(resume_data.get("experience", []))
    if exp_count >= 3:
        strengths.append(f"Consistent work history ({exp_count} positions)")
    job_industry = (job_data.get("industry") or "").lower()
    exp_industries = [e.get("industry", "") for e in resume_data.get("experience", [])]
    if job_industry and any(job_industry in ind.lower() for ind in exp_industries if ind):
        strengths.append("Industry experience matches")
    return strengths


def _hm_concerns(resume_data: dict, job_data: dict) -> list:
    concerns = []
    job_years = job_data.get("years_experience_required", 0) or job_data.get("years_required", 0)
    cand_years = resume_data.get("years_of_experience", 0) or _compute_experience_years(resume_data)
    if job_years and cand_years < job_years * 0.7:
        concerns.append(f"Only {cand_years} years vs {job_years} required")
    if cand_years and job_years and cand_years >= job_years * 2:
        concerns.append("May be overqualified for role level")
    return concerns


def _tech_skill_gaps(resume_data: dict, job_data: dict) -> list:
    gaps = []
    job_tech = set(
        t.lower() for t in (
            job_data.get("required_skills", []) +
            job_data.get("technologies", []) +
            job_data.get("tools", [])
        )
    )
    resume_tech = set(
        s.lower() for s in (
            resume_data.get("skills", []) +
            resume_data.get("technologies", [])
        )
    )
    missing = job_tech - resume_tech
    if missing:
        for tech in sorted(missing)[:8]:
            gaps.append(tech)
    return gaps


def _compute_experience_years(resume_data: dict) -> int:
    total_months = 0
    for exp in resume_data.get("experience", []):
        start = exp.get("start_date", "")
        end = exp.get("end_date", "") or exp.get("current", False) and "Present"
        if not start or not end:
            continue
        try:
            parts = start.split("-")
            start_year = int(parts[0])
            start_month = int(parts[1]) if len(parts) > 1 else 1
            if end.lower() == "present":
                import datetime
                now = datetime.datetime.now()
                end_year, end_month = now.year, now.month
            else:
                parts = end.split("-")
                end_year = int(parts[0])
                end_month = int(parts[1]) if len(parts) > 1 else 1
            total_months += (end_year - start_year) * 12 + (end_month - start_month)
        except (ValueError, IndexError):
            continue
    return total_months // 12 if total_months else resume_data.get("years_of_experience", 0) or 0


def _is_recent(exp: dict) -> bool:
    import datetime
    end = exp.get("end_date", "") or ""
    if end.lower() == "present" or not end:
        return True
    try:
        parts = end.split("-")
        end_year = int(parts[0])
        return end_year >= datetime.datetime.now().year - 3
    except (ValueError, IndexError):
        return False


def _evaluate_portfolio_quality(resume_data: dict) -> tuple:
    score = 40
    reasons = []
    projects = resume_data.get("projects", [])
    if projects:
        total_bullets = sum(len(p.get("bullets", []) or []) for p in projects)
        has_tech = sum(1 for p in projects if p.get("technologies"))
        has_description = sum(1 for p in projects if p.get("description") and len(p.get("description", "")) > 20)
        depth_score = min(total_bullets * 5, 20)
        coverage_score = min((has_tech + has_description) * 5, 15)
        score += depth_score + coverage_score
        reasons.append(f"{len(projects)} projects, {total_bullets} bullets, {has_tech} with tech stack")
    for exp in resume_data.get("experience", []):
        for b in exp.get("bullets", []):
            lower_b = b.lower()
            if any(kw in lower_b for kw in ["portfolio", "github.com", "gitlab.com", "open source", "side project"]):
                score += 8
                reasons.append("Portfolio link/project in work experience")
                break
    if not projects:
        reasons.append("No projects section — candidates with portfolios interview 40% more")
    return min(100, max(0, score)), "; ".join(reasons) if reasons else "No portfolio evidence"


def _evaluate_github_presence(resume_data: dict) -> tuple:
    score = 30
    reasons = []
    links = resume_data.get("links", resume_data.get("urls", []))
    has_gh_link = False
    if links:
        for link in links:
            if isinstance(link, str):
                if "github.com" in link.lower():
                    has_gh_link = True
                    score += 25
                    reasons.append("GitHub profile URL provided")
                elif "gitlab.com" in link.lower():
                    score += 20
                    reasons.append("GitLab profile URL provided")
    summary = (resume_data.get("summary") or "").lower()
    if "github" in summary or "open source" in summary:
        score += 10
        if not has_gh_link:
            reasons.append("Open source mentioned in summary")
    skills = [s.lower() for s in resume_data.get("skills", [])]
    if "git" in skills:
        score += 3
        if not reasons:
            reasons.append("Git listed as skill")
    for exp in resume_data.get("experience", []):
        for b in exp.get("bullets", []):
            lower_b = b.lower()
            if "pull request" in lower_b or "code review" in lower_b or "open source" in lower_b:
                score += 8
                reasons.append("Active OSS contribution mentioned in experience")
                break
    return min(100, max(0, score)), "; ".join(reasons) if reasons else "No GitHub presence detected"


def _evaluate_project_relevance(resume_data: dict, job_data: dict) -> tuple:
    if not job_data:
        return 50, ["No job data for comparison"]
    score = 40
    reasons = []
    job_skills = set(s.lower() for s in job_data.get("required_skills", []))
    job_industry = (job_data.get("industry") or "").lower()
    projects = resume_data.get("projects", [])
    project_skill_matches = set()
    for proj in projects:
        proj_text = (proj.get("description", "") + " " + " ".join(proj.get("technologies", []))).lower()
        matched = {s for s in job_skills if s in proj_text}
        project_skill_matches.update(matched)
        if matched:
            score += min(len(matched) * 5, 15)
    if project_skill_matches:
        reasons.append(f"Projects match {len(project_skill_matches)} job skills: {', '.join(sorted(project_skill_matches)[:4])}")

    # Experience relevance
    exp_skill_matches = set()
    for exp in resume_data.get("experience", []):
        bullets_text = " ".join(exp.get("bullets", [])).lower()
        matched = {s for s in job_skills if s in bullets_text}
        exp_skill_matches.update(matched)
    if exp_skill_matches:
        overlap_count = len(exp_skill_matches)
        score += min(overlap_count * 4, 15)
        if not reasons:
            reasons.append(f"Experience aligns with {overlap_count} required skills")

    # Industry relevance
    if job_industry:
        for exp in resume_data.get("experience", []):
            exp_industry = (exp.get("industry") or "").lower()
            if job_industry in exp_industry or exp_industry in job_industry:
                score += 10
                reasons.append(f"Relevant {job_industry} industry experience")
                break
    return min(100, max(0, score)), "; ".join(reasons) if reasons else "No relevant projects identified"


def _evaluate_cultural_fit(resume_data: dict, job_data: dict, cover_letter_text: str) -> tuple:
    score = 50
    reasons = []
    cover_lower = (cover_letter_text or "").lower()
    summary = (resume_data.get("summary", "") or "").lower()
    job_industry = (job_data.get("industry") or "").lower() if job_data else ""
    job_description = (job_data.get("description") or "").lower() if job_data else ""

    # Industry domain language alignment
    if job_industry:
        industry_terms = job_industry.split()
        cover_matches = sum(1 for t in industry_terms if t in cover_lower)
        if cover_matches >= 2:
            score += 10
            reasons.append(f"Industry language in cover letter ({cover_matches} terms)")

    # Extract cultural values from job description
    culture_signals = {
        "collaboration": ["team", "collaborat", "cross-functional", "together"],
        "innovation": ["innovate", "creative", "new ideas", "forward-thinking"],
        "growth": ["learn", "grow", "develop", "mentor", "coach"],
        "ownership": ["ownership", "autonomy", "self-starter", "drive"],
        "excellence": ["quality", "excellence", "high standard", "rigor"],
        "diversity": ["diverse", "inclusion", "belonging", "equity"],
        "impact": ["impact", "results", "outcome", "mission-driven"],
    }

    # What does the job description emphasize?
    job_values = set()
    for value, keywords in culture_signals.items():
        if any(kw in job_description for kw in keywords):
            job_values.add(value)

    # Does the candidate mirror those values?
    matched_values = []
    for value in job_values:
        keywords = culture_signals[value]
        if any(kw in cover_lower for kw in keywords) or any(kw in summary for kw in keywords):
            matched_values.append(value)
            score += 8
    if matched_values:
        reasons.append(f"Candidate mirrors job values: {', '.join(matched_values)}")

    # Communication style match — formal vs casual
    formal_indicators = ["demonstrate", "utilize", "subsequently", "nevertheless", "moreover"]
    casual_indicators = ["i've", "i'm", "i'd", "love to", "excited about", "passionate"]
    formal_score = sum(1 for w in formal_indicators if w in cover_lower)
    casual_score = sum(1 for w in casual_indicators if w in cover_lower)
    if formal_score > casual_score:
        score += 3
        reasons.append("Formal communication style")
    elif casual_score > formal_score:
        score += 3
        reasons.append("Casual communication style")

    return min(100, max(0, score)), "; ".join(reasons) if reasons else "No cultural fit signals detected"


def _evaluate_communication_quality(cover_letter_text: str) -> tuple:
    if not cover_letter_text or len(cover_letter_text.strip()) < 50:
        return 30, ["No cover letter to evaluate"]
    score = 50
    reasons = []
    words = cover_letter_text.split()
    wc = len(words)
    if 120 <= wc <= 280:
        score += 10
        reasons.append(f"Optimal length ({wc} words)")
    elif 80 <= wc < 120 or 280 < wc <= 400:
        score += 3
        reasons.append(f"Acceptable length ({wc} words)")
    else:
        score -= 10
        reasons.append(f"Poor length ({wc} words)")

    lower = cover_letter_text.lower()
    first_person_pronouns = ["i've", "i'm", "i'll", "i'd", "my", "me"]
    fp_count = sum(1 for p in first_person_pronouns if p in lower)
    if fp_count >= 4:
        score += 10
        reasons.append("Strong first-person voice")
    elif fp_count >= 2:
        score += 5
        reasons.append("Some first-person voice")
    else:
        score -= 5
        reasons.append("Limited first-person voice — reads impersonally")

    # Grammar/structure checks
    if cover_letter_text.strip().endswith((".", "!", "?")):
        score += 3
        reasons.append("Proper sentence termination")

    has_greeting = bool(re.search(r'(?i)^(dear|hi|hello|to\s+the|greetings)', cover_letter_text.strip()))
    has_signoff = bool(re.search(r'(?i)(sincerely|best|thanks|regards|warmly|cheers)\s*$', cover_letter_text.strip()))
    if has_greeting and has_signoff:
        score += 5
        reasons.append("Proper letter structure (greeting + sign-off)")
    elif has_greeting or has_signoff:
        score += 2

    # Sentence variety
    sentences = re.split(r'[.!?]+', cover_letter_text)
    valid = [s.strip() for s in sentences if len(s.strip().split()) > 2]
    if len(valid) >= 3:
        lengths = [len(s.split()) for s in valid]
        avg_len = sum(lengths) / len(lengths)
        variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
        if variance > 40:
            score += 5
            reasons.append("High sentence length variety")
        elif variance > 20:
            score += 2
            reasons.append("Moderate sentence variety")
        elif variance < 10:
            score -= 8
            reasons.append("Uniform sentence length — robotic")
    paragraphs = [p.strip() for p in cover_letter_text.split("\n\n") if p.strip()]
    if 2 <= len(paragraphs) <= 5:
        if len(paragraphs) != 3:
            score += 3
            reasons.append("Non-default paragraph structure")
    else:
        score -= 3
        reasons.append("Poor paragraph structure")
    score = max(0, min(100, score))
    return score, "; ".join(reasons) if reasons else "Basic communication"


def _has_proper_salutation_closing(text: str) -> bool:
    if not text:
        return False
    salutations = ["dear", "hello", "hi ", "to the", "greetings"]
    closings = ["sincerely", "best regards", "thank you", "yours truly", "warmly", "best"]
    has_sal = any(s in text[:100].lower() for s in salutations)
    has_clo = any(c in text[-200:].lower() for c in closings)
    return has_sal or has_clo


AI_PHRASE_PATTERNS = [
    "i am writing to apply", "i am excited to", "i am thrilled to",
    "i would be honored", "it is with great enthusiasm", "proven track record",
    "i am confident that my", "i possess the", "i am eager to",
    "please find attached", "i have attached", "as you can see from my",
    "i believe that my skills", "i am a highly motivated",
    "i am writing this letter", "thank you for your time and consideration",
    "i look forward to hearing from you", "i am interested in",
    "i am passionate about", "i am writing to express my interest",
]


def _looks_ai_generated(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    hits = sum(1 for p in AI_PHRASE_PATTERNS if p in lower)
    if hits >= 3:
        return True
    words = text.split()
    if len(words) > 400:
        return False
    if 180 <= len(words) <= 220 and hits >= 2:
        return True
    sentences = re.split(r'[.!?]+', text)
    valid = [s.strip() for s in sentences if len(s.strip().split()) > 3]
    if len(valid) >= 3:
        lengths = [len(s.split()) for s in valid]
        avg_len = sum(lengths) / len(lengths)
        variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
        if variance < 15 and 15 <= avg_len <= 22:
            return True
    return False
