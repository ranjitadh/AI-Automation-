import logging
import re

logger = logging.getLogger(__name__)

ATS_PLATFORMS = [
    {
        "name": "LinkedIn",
        "domain": "linkedin.com",
        "max_field_length": 1000,
        "supports_html": False,
        "parsing_quality": "high",
        "bullet_recommendation": "short",
        "skill_weight": "high",
    },
    {
        "name": "Greenhouse",
        "domain": "greenhouse.io",
        "max_field_length": 2000,
        "supports_html": False,
        "parsing_quality": "high",
        "bullet_recommendation": "standard",
        "skill_weight": "high",
    },
    {
        "name": "Lever",
        "domain": "lever.co",
        "max_field_length": 2000,
        "supports_html": True,
        "parsing_quality": "high",
        "bullet_recommendation": "standard",
        "skill_weight": "medium",
    },
    {
        "name": "Workday",
        "domain": "myworkdayjobs.com",
        "max_field_length": 4000,
        "supports_html": False,
        "parsing_quality": "medium",
        "bullet_recommendation": "detailed",
        "skill_weight": "medium",
    },
    {
        "name": "Ashby",
        "domain": "ashbyhq.com",
        "max_field_length": 1500,
        "supports_html": False,
        "parsing_quality": "high",
        "bullet_recommendation": "standard",
        "skill_weight": "high",
    },
    {
        "name": "SmartRecruiters",
        "domain": "smartrecruiters.com",
        "max_field_length": 2000,
        "supports_html": False,
        "parsing_quality": "high",
        "bullet_recommendation": "standard",
        "skill_weight": "high",
    },
    {
        "name": "BambooHR",
        "domain": "bamboohr.com",
        "max_field_length": 1500,
        "supports_html": False,
        "parsing_quality": "medium",
        "bullet_recommendation": "short",
        "skill_weight": "medium",
    },
    {
        "name": "Indeed",
        "domain": "indeed.com",
        "max_field_length": 500,
        "supports_html": False,
        "parsing_quality": "low",
        "bullet_recommendation": "short",
        "skill_weight": "low",
    },
]


def evaluate_ats_compatibility(resume_data: dict) -> dict:
    results = []
    for platform in ATS_PLATFORMS:
        score = _score_for_platform(resume_data, platform)
        results.append(score)

    overall = sum(r["compatibility_score"] for r in results) / len(results) if results else 0
    weakest = min(results, key=lambda r: r["compatibility_score"]) if results else None
    strongest = max(results, key=lambda r: r["compatibility_score"]) if results else None

    improvements = []
    if results:
        common_issues = {}
        for r in results:
            for issue in r.get("issues", []):
                common_issues[issue] = common_issues.get(issue, 0) + 1
        for issue, count in sorted(common_issues.items(), key=lambda x: -x[1]):
            if count >= len(results) * 0.5:
                improvements.append({
                    "issue": issue,
                    "affected_platforms": count,
                    "total_platforms": len(results),
                    "priority": "high" if count >= len(results) * 0.75 else "medium",
                })

    return {
        "overall_ats_compatibility": round(overall, 1),
        "platform_scores": results,
        "weakest_platform": weakest["name"] if weakest else None,
        "weakest_score": weakest["compatibility_score"] if weakest else 0,
        "strongest_platform": strongest["name"] if strongest else None,
        "strongest_score": strongest["compatibility_score"] if strongest else 0,
        "priority_improvements": improvements,
    }


def _score_for_platform(resume_data: dict, platform: dict) -> dict:
    score = 75
    issues = []
    strengths = []

    exp_entries = resume_data.get("experience", [])
    skills = resume_data.get("skills", [])
    summary = resume_data.get("summary", "")

    if not summary:
        score -= 10
        issues.append("Missing professional summary")
    elif len(summary.split()) > platform["max_field_length"] // 20:
        score -= 3
        issues.append(f"Summary too long for {platform['name']}")

    bullet_too_long = 0
    total_bullets = 0
    for exp in exp_entries:
        for bullet in exp.get("bullets", []):
            total_bullets += 1
            words = len(bullet.split())
            if platform["bullet_recommendation"] == "short" and words > 20:
                bullet_too_long += 1
            elif platform["bullet_recommendation"] == "standard" and words > 30:
                bullet_too_long += 1

    if total_bullets > 0 and bullet_too_long / total_bullets > 0.5:
        score -= 5
        issues.append(f"Bullet points too detailed for {platform['name']} parsing")
    elif total_bullets > 0 and bullet_too_long == 0:
        score += 3
        strengths.append("Bullet length optimal for this ATS")

    if not skills:
        score -= 8
        issues.append("No skills section")
    elif platform["skill_weight"] == "high" and len(skills) >= 10:
        score += 5
        strengths.append("Strong skill coverage")

    exp_count = len(exp_entries)
    if exp_count == 0:
        score -= 15
        issues.append("No experience entries")
    elif exp_count >= 3:
        score += 3
        strengths.append("Solid work history")

    if platform["supports_html"]:
        if _has_html_formatting(summary):
            score += 5
            strengths.append("Can use HTML formatting")

    if platform["parsing_quality"] == "low":
        if exp_count > 5:
            score -= 3
            issues.append("Many entries may confuse basic parser")
        if len(skills) > 20:
            score -= 2
            issues.append("Large skill list may be truncated")

    score = max(0, min(100, score))
    return {
        "name": platform["name"],
        "domain": platform["domain"],
        "compatibility_score": score,
        "parsing_quality": platform["parsing_quality"],
        "field_length_limit": platform["max_field_length"],
        "strengths": strengths,
        "issues": issues,
        "recommendations": _generate_platform_recommendations(platform, issues, resume_data),
    }


def _generate_platform_recommendations(platform: dict, issues: list, resume_data: dict) -> list:
    recs = []

    if "Missing professional summary" in issues:
        recs.append("Add a 2-3 sentence professional summary")
    if "No skills section" in issues:
        recs.append("Add a dedicated skills section with 8-15 relevant skills")
    if "No experience entries" in issues:
        recs.append("Add at least 2-3 relevant experience entries")
    if any("too long" in i for i in issues):
        max_words = 20 if platform["bullet_recommendation"] == "short" else 30
        recs.append(f"Keep bullet points under {max_words} words for better parsing")
    if platform["parsing_quality"] == "low":
        recs.append("Use standard section headers (Experience, Skills, Education)")
        recs.append("Avoid columns, tables, or graphics")
    if platform["supports_html"]:
        recs.append("Leverage HTML formatting for emphasis where appropriate")

    if not recs:
        recs.append("Resume is well-optimized for this ATS")

    return recs


def _has_html_formatting(text: str) -> bool:
    html_tags = ["<b>", "<i>", "<u>", "<ul>", "<li>", "<br>", "<p>", "<strong>", "<em>"]
    return any(tag in text for tag in html_tags)


STANDARD_SECTION_HEADERS = [
    "experience", "work experience", "professional experience", "employment",
    "education", "academic background", "certifications",
    "skills", "technical skills", "core competencies", "expertise",
    "summary", "professional summary", "profile", "about me",
    "projects", "key projects", "project experience",
    "publications", "patents", "honors", "awards",
]


_STOP_WORDS = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
               "of", "with", "by", "as", "is", "was", "are", "were", "be", "been",
               "being", "have", "has", "had", "do", "does", "did", "will", "would",
               "could", "should", "may", "might", "shall", "can", "need", "dare",
               "ought", "used", "about", "above", "across", "after", "along",
               "also", "among", "any", "because", "before", "between", "both",
               "each", "few", "from", "how", "just", "more", "most", "much",
               "no", "not", "now", "only", "other", "own", "same", "so", "some",
               "such", "than", "that", "their", "them", "then", "there", "these",
               "they", "this", "through", "under", "up", "very", "what", "when",
               "where", "which", "while", "who", "why"} | set([str(i) for i in range(200)])


def _tokenize(text: str) -> list:
    tokens = re.findall(r'[a-zA-Z][a-zA-Z0-9+#.\-]*', text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


def analyze_keyword_density(resume_data: dict, job_data: dict) -> dict:
    job_skills = set(s.lower() for s in job_data.get("required_skills", [])) if job_data else set()
    if not job_skills:
        return {"keyword_density": 1.0, "matched_keywords": [], "missing_keywords": [], "density_score": 100}

    resume_text_parts = []
    resume_text_parts.append((resume_data.get("summary") or "").lower())
    for s in resume_data.get("skills", []):
        resume_text_parts.append(s.lower())
    for exp in resume_data.get("experience", []):
        resume_text_parts.append((exp.get("title") or "").lower())
        for b in exp.get("bullets", []):
            resume_text_parts.append(b.lower())
    resume_text = " ".join(resume_text_parts)
    resume_tokens = _tokenize(resume_text)

    matched = []
    missing = []
    for skill in job_skills:
        # Word-boundary matching to prevent "java" matching "javascript"
        pattern = r'(?<![a-z])' + re.escape(skill) + r'(?![a-z])'
        count = len(re.findall(pattern, resume_text))
        if count > 0:
            matched.append({"keyword": skill, "count": count})
        else:
            # Try normalized matching for compound skills
            skill_tokens = _tokenize(skill)
            if skill_tokens and all(t in resume_tokens for t in skill_tokens):
                matched.append({"keyword": skill, "count": 1, "matched_via": "tokenized"})
            else:
                missing.append(skill)

    total_density = sum(m["count"] for m in matched)
    total_words = len(resume_text.split())
    density = total_density / max(total_words, 1)

    match_pct = len(matched) / len(job_skills) if job_skills else 1.0
    density_score = int(match_pct * 60 + min(density * 500, 40))

    return {
        "keyword_density": round(density, 4),
        "matched_keywords": sorted(matched, key=lambda x: -x["count"])[:15],
        "missing_keywords": missing[:15],
        "match_percentage": round(match_pct * 100, 1),
        "density_score": min(100, density_score),
    }


def check_section_header_compliance(resume_data: dict) -> dict:
    found_headers = set()
    text = (resume_data.get("summary") or "")
    for exp in resume_data.get("experience", []):
        text += "\n" + (exp.get("title") or "")
        for b in exp.get("bullets", []):
            text += "\n" + b

    text_lower = text.lower()
    # Only match at line beginnings or as standalone section headers
    for header in STANDARD_SECTION_HEADERS:
        pattern = r'(?:^|\n)' + re.escape(header) + r'\s*[\n:]'
        if re.search(pattern, text_lower, re.MULTILINE):
            found_headers.add(header)

    required = {"experience", "skills", "education"}
    if resume_data.get("summary"):
        required.add("summary")

    missing = required - found_headers
    compliance = (len(found_headers & required) / len(required)) * 100 if required else 100

    return {
        "found_headers": sorted(found_headers),
        "required_headers": sorted(required),
        "missing_headers": sorted(missing),
        "compliance_percentage": round(compliance, 1),
    }


def check_formatting_compliance(resume_data: dict) -> dict:
    issues = []
    score = 100

    for exp in resume_data.get("experience", []):
        for b in exp.get("bullets", []):
            if b.startswith(" ") or b.startswith("\t"):
                issues.append("Bullet point has leading whitespace")
                score -= 2
                break

    exp_count = len(resume_data.get("experience", []))
    if exp_count > 10:
        issues.append(f"Too many experience entries ({exp_count}) — ATS may truncate")
        score -= 5

    summary = resume_data.get("summary", "")
    if len(summary.split()) > 100:
        issues.append("Summary section too long")
        score -= 3

    for exp in resume_data.get("experience", []):
        title = exp.get("title", "")
        if len(title) > 100:
            issues.append("Job title exceeds 100 characters")
            score -= 2
            break

    skills = resume_data.get("skills", [])
    if len(skills) > 40:
        issues.append(f"Large skill list ({len(skills)}) may overwhelm ATS")
        score -= 3

    for exp in resume_data.get("experience", []):
        bullets = exp.get("bullets", [])
        if len(bullets) > 10:
            issues.append(f"Too many bullets under one position ({len(bullets)})")
            score -= 2
            break

    return {
        "formatting_score": max(0, score),
        "issues": issues,
    }


def check_resume_section_validity(resume_data: dict) -> dict:
    checks = []
    errors = []

    experience = resume_data.get("experience", [])
    if experience:
        for i, exp in enumerate(experience):
            if not exp.get("title"):
                errors.append(f"Experience entry {i+1} missing job title")
            if not exp.get("start_date"):
                errors.append(f"Experience entry {i+1} missing start date")
            if exp.get("bullets") is None:
                errors.append(f"Experience entry {i+1} has no bullets field")
    else:
        errors.append("No experience entries found")

    for field in ["skills", "summary"]:
        if field not in resume_data or not resume_data.get(field):
            errors.append(f"Missing '{field}' in resume")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "checks": checks,
    }


def get_ats_optimization_suggestions(resume_data: dict, job_platform: str = None, job_data: dict = None) -> list:
    suggestions = []

    # Check section header compliance
    header_result = check_section_header_compliance(resume_data)
    if header_result["missing_headers"]:
        suggestions.append(f"[HIGH] Missing standard ATS section headers: {', '.join(header_result['missing_headers'])}")

    # Check formatting
    fmt_result = check_formatting_compliance(resume_data)
    for issue in fmt_result["issues"]:
        suggestions.append(f"[MEDIUM] {issue}")

    # Check keyword density
    if job_data:
        kw_result = analyze_keyword_density(resume_data, job_data)
        if kw_result["density_score"] < 70:
            suggestions.append(f"[HIGH] Low keyword density score ({kw_result['density_score']}/100). Missing {len(kw_result['missing_keywords'])} required keywords")
        if kw_result["match_percentage"] < 60:
            suggestions.append(f"[HIGH] Only {kw_result['match_percentage']}% of job skills mentioned in resume")

    # Check section validity
    valid_result = check_resume_section_validity(resume_data)
    for err in valid_result["errors"]:
        suggestions.append(f"[HIGH] {err}")

    if job_platform:
        platform = next((p for p in ATS_PLATFORMS if p["domain"] in job_platform), None)
        if platform:
            result = _score_for_platform(resume_data, platform)
            suggestions.extend(result["recommendations"])

    eval_result = evaluate_ats_compatibility(resume_data)
    for imp in eval_result.get("priority_improvements", []):
        suggestions.append(f"[{imp['priority'].upper()}] {imp['issue']} (affects {imp['affected_platforms']}/{imp['total_platforms']} platforms)")

    if not suggestions:
        suggestions.append("Resume is well-optimized across all major ATS platforms")

    return suggestions
