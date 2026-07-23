from __future__ import annotations

import json
import re
from datetime import datetime, timezone


def _safe_str(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _truncate(text: str | None, limit: int = 500) -> str | None:
    if not text:
        return None
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] if len(text) > limit else text


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_salary(item: dict) -> str | None:
    min_sal = item.get("minSal", 0)
    max_sal = item.get("maxSal", 0)
    hide_sal = item.get("hideSal", 1)
    if hide_sal or (not min_sal and not max_sal):
        return None
    if min_sal and max_sal:
        return f"{min_sal}-{max_sal} LPA"
    if min_sal:
        return f"{min_sal}+ LPA"
    return f"Up to {max_sal} LPA"


def _format_experience(item: dict) -> str | None:
    exp_min = item.get("min")
    exp_max = item.get("max")
    if exp_min is None and exp_max is None:
        return None
    if exp_min is not None and exp_max is not None:
        return f"{exp_min}-{exp_max} years"
    if exp_min is not None:
        return f"{exp_min}+ years"
    return f"Up to {exp_max} years"


def _format_locations(item: dict) -> str | None:
    locations = item.get("locations") or item.get("location")
    if not locations:
        return _safe_str(item.get("otherLocation"))
    if isinstance(locations, list):
        names = [loc.get("name", "") for loc in locations if isinstance(loc, dict)]
        names = [n for n in names if n]
        if names:
            return ", ".join(names)
    return None


def _format_tags(item: dict) -> list[str] | None:
    tags = item.get("tags")
    if not tags or not isinstance(tags, list):
        return None
    names = [t.get("name", "") for t in tags if isinstance(t, dict)]
    names = [n for n in names if n]
    return names if names else None


def _format_posted_date(item: dict) -> str | None:
    ts = item.get("createdTime") or item.get("createdTimeMs")
    if not ts:
        return None
    try:
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except (OSError, ValueError):
        return None


FUNCTIONAL_AREA_MAP = {
    1: "IT",
    2: "Finance & Accounts",
    3: "Marketing",
    4: "HR",
    5: "Operations",
    6: "Analytics",
    7: "Consulting",
    8: "Sales",
    9: "Strategy",
    10: "General Management",
    11: "Supply Chain",
    12: "Legal",
    13: "Banking",
    14: "Engineering",
    15: "Sales & Business Development",
    16: "Product Management",
    17: "Research",
    18: "Media",
    19: "Education",
    20: "Design",
}

INDUSTRY_MAP = {
    1: "IT/Software",
    2: "BFSI",
    3: "Consulting",
    4: "FMCG",
    5: "Manufacturing",
    6: "Healthcare",
    7: "Recruitment",
    8: "Retail",
    9: "E-Commerce",
    10: "Education",
    11: "Telecom",
    12: "Media",
    13: "Real Estate",
    14: "Automotive",
    15: "Energy",
}


def parse_api_response(data: dict) -> tuple[list[dict], bool]:
    jobs: list[dict] = []
    items = data.get("data", [])
    has_more = data.get("hasMore", False)

    for item in items:
        if not isinstance(item, dict):
            continue
        job = _normalize_api_job(item)
        if job:
            jobs.append(job)

    return jobs, has_more


def _normalize_api_job(item: dict) -> dict | None:
    title = _safe_str(item.get("title") or item.get("jobdesignation"))
    if not title:
        return None

    job_url = item.get("jobDetailUrl")
    if not job_url:
        job_id = item.get("id")
        if job_id:
            job_url = f"https://www.iimjobs.com/j/{job_id}"
        else:
            return None

    company_data = item.get("companyData") or {}
    company_name = company_data.get("companyName") if isinstance(company_data, dict) else None

    func_area = item.get("functionalArea")
    func_str = None
    if isinstance(func_area, int):
        func_str = FUNCTIONAL_AREA_MAP.get(func_area)
    elif func_area:
        func_str = str(func_area)

    industry_val = item.get("industry")
    industry_str = None
    if industry_val:
        try:
            industry_str = INDUSTRY_MAP.get(int(industry_val))
        except (ValueError, TypeError):
            industry_str = str(industry_val)

    is_urgent = bool(
        item.get("premium")
        or item.get("star")
        or item.get("brandedJd")
    )

    return {
        "jobTitle": title,
        "companyName": _safe_str(company_name),
        "jobUrl": job_url,
        "location": _format_locations(item),
        "experience": _format_experience(item),
        "salary": _format_salary(item),
        "jobFunction": func_str,
        "industry": industry_str,
        "postedDate": _format_posted_date(item),
        "applicationDeadline": None,
        "jobDescription": None,
        "skills": _format_tags(item),
        "educationRequired": None,
        "jobType": None,
        "companyUrl": None,
        "isUrgent": is_urgent,
        "scrapedAt": _now_iso(),
    }


def extract_next_data(html: str) -> dict | None:
    m = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
    )
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def parse_jobs_from_html(html: str) -> list[dict]:
    jobs: list[dict] = []

    ld_json_blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    for block in ld_json_blocks:
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    job = _parse_ld_job(item)
                    if job:
                        jobs.append(job)
        elif isinstance(data, dict):
            if data.get("@type") == "JobPosting":
                job = _parse_ld_job(data)
                if job:
                    jobs.append(job)

    if jobs:
        return jobs

    link_pattern = re.findall(
        r'<a[^>]*href="(https://www\.iimjobs\.com/j/[^"]+)"[^>]*>(.*?)</a>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    for href, link_text in link_pattern:
        title = re.sub(r"<[^>]+>", "", link_text).strip()
        if title and len(title) > 3:
            jobs.append({
                "jobTitle": title,
                "companyName": None,
                "jobUrl": href,
                "location": None,
                "experience": None,
                "salary": None,
                "jobFunction": None,
                "industry": None,
                "postedDate": None,
                "applicationDeadline": None,
                "jobDescription": None,
                "skills": None,
                "educationRequired": None,
                "jobType": None,
                "companyUrl": None,
                "isUrgent": False,
                "scrapedAt": _now_iso(),
            })

    return jobs


def _parse_ld_job(item: dict) -> dict | None:
    title = item.get("title") or item.get("name")
    url = item.get("url") or item.get("sameAs")
    if not title or not url:
        return None

    org = item.get("hiringOrganization") or {}
    company = org.get("name") if isinstance(org, dict) else str(org)

    loc = item.get("jobLocation")
    location_str = None
    if isinstance(loc, dict):
        addr = loc.get("address", {})
        location_str = addr.get("addressLocality") if isinstance(addr, dict) else str(addr)
    elif isinstance(loc, list) and loc:
        parts = []
        for l in loc:
            if isinstance(l, dict):
                a = l.get("address", {})
                parts.append(a.get("addressLocality", "") if isinstance(a, dict) else str(a))
        location_str = ", ".join(p for p in parts if p)

    return {
        "jobTitle": title.strip(),
        "companyName": _safe_str(company),
        "jobUrl": url,
        "location": _safe_str(location_str),
        "experience": _safe_str(item.get("experienceRequirements")),
        "salary": None,
        "jobFunction": _safe_str(item.get("occupationalCategory")),
        "industry": _safe_str(item.get("industry")),
        "postedDate": _safe_str(item.get("datePosted")),
        "applicationDeadline": _safe_str(item.get("validThrough")),
        "jobDescription": _truncate(item.get("description")),
        "skills": None,
        "educationRequired": None,
        "jobType": _safe_str(item.get("employmentType")),
        "companyUrl": _safe_str(org.get("url") if isinstance(org, dict) else None),
        "isUrgent": False,
        "scrapedAt": _now_iso(),
    }
