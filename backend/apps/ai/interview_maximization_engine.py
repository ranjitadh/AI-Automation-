import logging
from collections import Counter, defaultdict

from .models import CareerMemory, ApplicationOutcome, ApplicationDecision

logger = logging.getLogger(__name__)


def compute_interview_maximization(user, organization) -> dict:
    outcomes = ApplicationOutcome.objects.filter(
        user=user, organization=organization
    ).select_related("application__job__company").order_by("-created_at")[:200]

    if not outcomes.exists():
        return _empty_result("No application outcomes to analyze")

    recommendations = _analyze_what_works(outcomes, user, organization)
    return {
        "has_data": True,
        "total_outcomes_analyzed": outcomes.count(),
        **recommendations,
    }


def get_optimal_resume_style(user, organization) -> dict:
    memories = CareerMemory.objects.filter(
        user=user, organization=organization,
        memory_type__in=["success_pattern", "failure_pattern"],
        is_active=True,
    ).order_by("-confidence")[:30]

    styles = {"professional": {"score": 0, "count": 0}, "direct": {"score": 0, "count": 0},
              "storytelling": {"score": 0, "count": 0}, "enthusiastic": {"score": 0, "count": 0}}

    for m in memories:
        val = m.value if isinstance(m.value, dict) else {}
        style = val.get("cover_letter_style", "")
        if style in styles:
            styles[style]["count"] += 1
            styles[style]["score"] += m.confidence

    best_style = max(styles, key=lambda s: styles[s]["score"]) if any(v["count"] > 0 for v in styles.values()) else "professional"

    return {
        "recommended_cover_letter_style": best_style,
        "style_performance": styles,
        "memory_patterns_used": memories.count(),
    }


def get_optimal_salary_range(user, organization) -> dict:
    interviews = ApplicationOutcome.objects.filter(
        user=user, organization=organization,
        outcome__in=["interview", "offer", "accepted"],
    ).select_related("application__job")

    salaries = []
    for o in interviews:
        job = o.application.job if hasattr(o.application, "job") else None
        if job and job.salary_max:
            salaries.append(float(job.salary_max))
        elif job and job.salary_min:
            salaries.append(float(job.salary_min))

    if not salaries:
        return {"has_data": False, "message": "No interview data to determine optimal salary"}

    avg = sum(salaries) / len(salaries)
    return {
        "has_data": True,
        "optimal_min": round(avg * 0.85),
        "optimal_max": round(avg * 1.15),
        "average_offer_salary": round(avg),
        "sample_size": len(salaries),
    }


def _analyze_what_works(outcomes, user, organization) -> dict:
    total = outcomes.count()
    interviews = outcomes.filter(outcome__in=["interview", "offer", "accepted"])
    interview_count = interviews.count()
    interview_rate = interview_count / total if total > 0 else 0

    rejected = outcomes.filter(outcome__in=["rejected", "no_response"])
    rejection_count = rejected.count()

    best_industries = _compute_best_industries(interviews, outcomes)
    best_titles = _compute_best_titles(interviews, outcomes)
    best_skills = _compute_best_skills(interviews, outcomes)
    best_resume_versions = _compute_best_resume_versions(interviews, outcomes)
    best_salary_range = _compute_best_salary_range(interviews, outcomes)

    optimal_size = _compute_optimal_company_size(interviews, outcomes)
    best_locations = _compute_best_locations(interviews, outcomes)

    max_patterns = CareerMemory.objects.filter(
        user=user, organization=organization,
        memory_type="success_pattern", is_active=True,
    ).order_by("-confidence")

    return {
        "interview_rate": round(interview_rate, 3),
        "interviews": interview_count,
        "rejections": rejection_count,
        "total_applications": total,
        "best_performing_industries": best_industries,
        "best_performing_titles": best_titles,
        "best_performing_skills": best_skills,
        "best_performing_resume_versions": best_resume_versions,
        "optimal_salary_range": best_salary_range,
        "optimal_company_size": optimal_size,
        "best_locations": best_locations,
        "top_success_patterns": [
            {
                "pattern": m.key,
                "confidence": m.confidence,
                "detail": m.value.get("detail", "") if isinstance(m.value, dict) else "",
            }
            for m in max_patterns[:5]
        ],
    }


def _compute_best_industries(interviews, all_outcomes) -> list:
    interview_industries = Counter()
    all_industries = Counter()

    for o in all_outcomes:
        job = getattr(o.application, "job", None) if hasattr(o.application, "job") else None
        if job and hasattr(job, "company") and job.company:
            industry = getattr(job.company, "industry", None) or job.company.name
            all_industries[industry] += 1
            if o.outcome in ["interview", "offer", "accepted"]:
                interview_industries[industry] += 1

    results = []
    for ind, total_count in all_industries.most_common(10):
        int_count = interview_industries.get(ind, 0)
        rate = int_count / total_count if total_count > 0 else 0
        if total_count >= 2:
            results.append({
                "industry": ind,
                "interview_rate": round(rate, 2),
                "applications": total_count,
                "interviews": int_count,
            })

    return sorted(results, key=lambda r: r["interview_rate"], reverse=True)


def _compute_best_titles(interviews, all_outcomes) -> list:
    interview_titles = Counter()
    all_titles = Counter()

    for o in all_outcomes:
        job = getattr(o.application, "job", None) if hasattr(o.application, "job") else None
        if job:
            title = job.title or ""
            normalized = _normalize_title(title)
            all_titles[normalized] += 1
            if o.outcome in ["interview", "offer", "accepted"]:
                interview_titles[normalized] += 1

    results = []
    for title, total_count in all_titles.most_common(10):
        int_count = interview_titles.get(title, 0)
        rate = int_count / total_count if total_count > 0 else 0
        if total_count >= 2:
            results.append({
                "title_pattern": title,
                "interview_rate": round(rate, 2),
                "applications": total_count,
                "interviews": int_count,
            })

    return sorted(results, key=lambda r: r["interview_rate"], reverse=True)


def _compute_best_skills(interviews, all_outcomes) -> list:
    interview_skills = Counter()
    all_skills = Counter()

    for o in all_outcomes:
        decision = ApplicationDecision.objects.filter(
            user=o.user, application=o.application
        ).first()
        if decision and decision.reasoning:
            from ..jobs.models import Job
            job = getattr(o.application, "job", None) if hasattr(o.application, "job") else None
            if job and job.required_skills:
                for skill in (job.required_skills if isinstance(job.required_skills, list) else []):
                    all_skills[skill.lower()] += 1
                    if o.outcome in ["interview", "offer", "accepted"]:
                        interview_skills[skill.lower()] += 1

    results = []
    for skill, total_count in all_skills.most_common(15):
        int_count = interview_skills.get(skill, 0)
        rate = int_count / total_count if total_count > 0 else 0
        if total_count >= 2:
            results.append({
                "skill": skill,
                "interview_rate": round(rate, 2),
                "appearances": total_count,
                "interviews": int_count,
            })

    return sorted(results, key=lambda r: r["interview_rate"], reverse=True)


def _compute_best_resume_versions(interviews, all_outcomes) -> list:
    version_interviews = Counter()
    version_total = Counter()

    for o in all_outcomes:
        version = o.resume_version_used or "default"
        version_total[version] += 1
        if o.outcome in ["interview", "offer", "accepted"]:
            version_interviews[version] += 1

    results = []
    for ver, total_count in version_total.most_common():
        int_count = version_interviews.get(ver, 0)
        rate = int_count / total_count if total_count > 0 else 0
        if total_count >= 2:
            results.append({
                "resume_version": ver,
                "interview_rate": round(rate, 2),
                "uses": total_count,
                "interviews": int_count,
            })

    return sorted(results, key=lambda r: r["interview_rate"], reverse=True)


def _compute_best_salary_range(interviews, all_outcomes) -> dict:
    salaries = []
    for o in all_outcomes:
        job = getattr(o.application, "job", None) if hasattr(o.application, "job") else None
        if job:
            if job.salary_max:
                salaries.append((float(job.salary_max), o.outcome))
            elif job.salary_min:
                salaries.append((float(job.salary_min), o.outcome))

    if not salaries:
        return {"average": 0, "min": 0, "max": 0, "sample": 0}

    interview_salaries = [s[0] for s in salaries if s[1] in ["interview", "offer", "accepted"]]
    if not interview_salaries:
        interview_salaries = [s[0] for s in salaries]

    avg = sum(interview_salaries) / len(interview_salaries) if interview_salaries else 0
    return {
        "optimal_min": round(avg * 0.85),
        "optimal_max": round(avg * 1.15),
        "average": round(avg),
        "sample_size": len(interview_salaries),
    }


def _compute_optimal_company_size(interviews, all_outcomes) -> dict:
    size_map = {"small": 0, "medium": 0, "large": 0, "enterprise": 0}
    size_interviews = {"small": 0, "medium": 0, "large": 0, "enterprise": 0}

    for o in all_outcomes:
        job = getattr(o.application, "job", None) if hasattr(o.application, "job") else None
        if job and hasattr(job, "company") and job.company:
            size = getattr(job.company, "size", None) or "unknown"
            if size in size_map:
                size_map[size] += 1
                if o.outcome in ["interview", "offer", "accepted"]:
                    size_interviews[size] += 1

    results = {}
    for size, total in size_map.items():
        if total > 0:
            rate = size_interviews[size] / total
            results[size] = {
                "interview_rate": round(rate, 2),
                "applications": total,
                "interviews": size_interviews[size],
            }

    return results


def _compute_best_locations(interviews, all_outcomes) -> list:
    interview_locs = Counter()
    all_locs = Counter()

    for o in all_outcomes:
        job = getattr(o.application, "job", None) if hasattr(o.application, "job") else None
        if job:
            loc = job.location or "remote"
            all_locs[loc] += 1
            if o.outcome in ["interview", "offer", "accepted"]:
                interview_locs[loc] += 1

    results = []
    for loc, total_count in all_locs.most_common(10):
        int_count = interview_locs.get(loc, 0)
        rate = int_count / total_count if total_count > 0 else 0
        if total_count >= 2:
            results.append({
                "location": loc,
                "interview_rate": round(rate, 2),
                "applications": total_count,
                "interviews": int_count,
            })

    return sorted(results, key=lambda r: r["interview_rate"], reverse=True)


def _normalize_title(title: str) -> str:
    t = title.lower().strip()
    for prefix in ["senior ", "sr ", "lead ", "principal ", "staff ", "head of ", "vp of ", "director of "]:
        t = t.replace(prefix, "")
    for suffix in [" ii", " iii", " iv", " (remote)", " (hybrid)"]:
        t = t.replace(suffix, "")
    return t.strip()


def _empty_result(msg: str) -> dict:
    return {
        "has_data": False,
        "message": msg,
        "interview_rate": 0,
        "interviews": 0,
        "rejections": 0,
        "total_applications": 0,
        "best_performing_industries": [],
        "best_performing_titles": [],
        "best_performing_skills": [],
        "best_performing_resume_versions": [],
        "optimal_salary_range": {},
        "optimal_company_size": {},
        "best_locations": [],
        "top_success_patterns": [],
    }
