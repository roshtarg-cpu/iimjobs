from __future__ import annotations

import json
import re
from datetime import datetime, timezone


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


def _safe_str(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _safe_list(val) -> list[str] | None:
    if not val:
        return None
    if isinstance(val, list):
        return [str(v).strip() for v in val if v] or None
    if isinstance(val, str):
        return [s.strip() for s in val.split(",") if s.strip()] or None
    return None


def _truncate(text: str | None, limit: int = 500) -> str | None:
    if not text:
        return None
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] if len(text) > limit else text


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_jobs_from_next_data(data: dict) -> list[dict]:
    jobs: list[dict] = []

    props = data.get("props", {}).get("pageProps", {})

    job_list = (
        props.get("jobs")
        or props.get("jobList")
        or props.get("searchResults")
        or props.get("data", {}).get("jobs")
        or props.get("data", {}).get("jobList")
        or props.get("initialData", {}).get("jobs")
        or []
    )

    if not job_list and isinstance(props.get("data"), list):
        job_list = props["data"]

    if not job_list:
        for key, val in props.items():
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                if any(
                    k in val[0]
                    for k in ("title", "jobTitle", "designation", "role")
                ):
                    job_list = val
                    break

    for item in job_list:
        if not isinstance(item, dict):
            continue
        job = _normalize_job(item)
        if job:
            jobs.append(job)

    return jobs


def _normalize_job(item: dict) -> dict | None:
    title = _safe_str(
        item.get("title")
        or item.get("jobTitle")
        or item.get("designation")
        or item.get("role")
    )
    if not title:
        return None

    job_id = item.get("id") or item.get("jobId") or item.get("encryptedId") or ""
    slug = item.get("slug") or item.get("seoUrl") or item.get("url") or ""

    if slug and slug.startswith("http"):
        job_url = slug
    elif slug:
        job_url = f"https://www.iimjobs.com{slug}" if slug.startswith("/") else f"https://www.iimjobs.com/{slug}"
    elif job_id:
        job_url = f"https://www.iimjobs.com/j/{job_id}"
    else:
        return None

    company = item.get("companyName") or item.get("company") or item.get("hiringOrganization")
    if isinstance(company, dict):
        company = company.get("name")

    location_val = item.get("location") or item.get("city") or item.get("locations")
    if isinstance(location_val, list):
        location_val = ", ".join(str(l) for l in location_val if l)
    elif isinstance(location_val, dict):
        location_val = location_val.get("name") or location_val.get("city")

    exp_min = item.get("minExperience") or item.get("expMin") or item.get("experienceMin")
    exp_max = item.get("maxExperience") or item.get("expMax") or item.get("experienceMax")
    experience = item.get("experience") or item.get("experienceRange")
    if not experience and exp_min is not None:
        experience = f"{exp_min}-{exp_max} years" if exp_max else f"{exp_min}+ years"

    salary_val = item.get("salary") or item.get("ctc") or item.get("salaryRange") or item.get("compensation")
    if isinstance(salary_val, dict):
        sal_min = salary_val.get("min") or salary_val.get("minSalary") or ""
        sal_max = salary_val.get("max") or salary_val.get("maxSalary") or ""
        salary_val = f"{sal_min}-{sal_max}" if sal_min else None

    skills_val = item.get("skills") or item.get("keySkills") or item.get("tags")
    if isinstance(skills_val, list) and skills_val and isinstance(skills_val[0], dict):
        skills_val = [s.get("name") or s.get("label") or str(s) for s in skills_val]

    return {
        "jobTitle": title,
        "companyName": _safe_str(company),
        "jobUrl": job_url,
        "location": _safe_str(location_val),
        "experience": _safe_str(experience),
        "salary": _safe_str(salary_val),
        "jobFunction": _safe_str(
            item.get("jobFunction")
            or item.get("function")
            or item.get("functionalArea")
            or item.get("category")
        ),
        "industry": _safe_str(
            item.get("industry") or item.get("industryType")
        ),
        "postedDate": _safe_str(
            item.get("postedDate")
            or item.get("createdAt")
            or item.get("publishedDate")
            or item.get("datePosted")
        ),
        "applicationDeadline": _safe_str(
            item.get("applicationDeadline")
            or item.get("deadline")
            or item.get("validThrough")
        ),
        "jobDescription": _truncate(
            item.get("jobDescription")
            or item.get("description")
            or item.get("snippet")
            or item.get("summary")
        ),
        "skills": _safe_list(skills_val),
        "educationRequired": _safe_str(
            item.get("educationRequired")
            or item.get("education")
            or item.get("qualification")
        ),
        "jobType": _safe_str(
            item.get("jobType")
            or item.get("employmentType")
            or item.get("type")
        ),
        "companyUrl": _safe_str(
            item.get("companyUrl")
            or item.get("companyWebsite")
        ),
        "isUrgent": bool(
            item.get("isUrgent")
            or item.get("urgent")
            or item.get("isPremium")
        ),
        "scrapedAt": _now_iso(),
    }


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
            items = data.get("itemListElement") or data.get("@graph") or []
            for item in items:
                if isinstance(item, dict):
                    posting = item.get("item", item)
                    if posting.get("@type") == "JobPosting":
                        job = _parse_ld_job(posting)
                        if job:
                            jobs.append(job)

    if jobs:
        return jobs

    card_patterns = [
        r'class="[^"]*job[-_]?card[^"]*"',
        r'class="[^"]*job[-_]?listing[^"]*"',
        r'class="[^"]*search[-_]?result[^"]*"',
        r'class="[^"]*job[-_]?item[^"]*"',
    ]

    for pattern in card_patterns:
        cards = re.findall(
            rf"<(?:div|article|li)[^>]*{pattern}[^>]*>(.*?)</(?:div|article|li)>",
            html,
            re.DOTALL | re.IGNORECASE,
        )
        if cards:
            for card_html in cards:
                job = _parse_card_html(card_html)
                if job:
                    jobs.append(job)
            break

    if not jobs:
        link_pattern = re.findall(
            r'<a[^>]*href="(/j/[^"]+)"[^>]*>(.*?)</a>',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        for href, link_text in link_pattern:
            title = re.sub(r"<[^>]+>", "", link_text).strip()
            if title and len(title) > 3:
                jobs.append(
                    {
                        "jobTitle": title,
                        "companyName": None,
                        "jobUrl": f"https://www.iimjobs.com{href}",
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
                    }
                )

    return jobs


def _parse_ld_job(item: dict) -> dict | None:
    title = item.get("title") or item.get("name")
    if not title:
        return None

    url = item.get("url") or item.get("sameAs") or ""
    if not url:
        return None

    org = item.get("hiringOrganization") or {}
    company = org.get("name") if isinstance(org, dict) else str(org)

    loc = item.get("jobLocation")
    location_str = None
    if isinstance(loc, dict):
        addr = loc.get("address", {})
        if isinstance(addr, dict):
            location_str = addr.get("addressLocality") or addr.get("name")
        else:
            location_str = str(addr)
    elif isinstance(loc, list) and loc:
        parts = []
        for l in loc:
            if isinstance(l, dict):
                a = l.get("address", {})
                parts.append(a.get("addressLocality", "") if isinstance(a, dict) else str(a))
        location_str = ", ".join(p for p in parts if p)

    salary_obj = item.get("baseSalary") or item.get("estimatedSalary")
    salary_str = None
    if isinstance(salary_obj, dict):
        val = salary_obj.get("value", {})
        if isinstance(val, dict):
            salary_str = f"{val.get('minValue', '')}-{val.get('maxValue', '')} {val.get('currency', '')}"
        else:
            salary_str = str(val)

    return {
        "jobTitle": title.strip(),
        "companyName": _safe_str(company),
        "jobUrl": url,
        "location": _safe_str(location_str),
        "experience": _safe_str(item.get("experienceRequirements")),
        "salary": _safe_str(salary_str),
        "jobFunction": _safe_str(item.get("occupationalCategory")),
        "industry": _safe_str(item.get("industry")),
        "postedDate": _safe_str(item.get("datePosted")),
        "applicationDeadline": _safe_str(item.get("validThrough")),
        "jobDescription": _truncate(item.get("description")),
        "skills": _safe_list(item.get("skills")),
        "educationRequired": _safe_str(
            item.get("educationRequirements", {}).get("credentialCategory")
            if isinstance(item.get("educationRequirements"), dict)
            else item.get("educationRequirements")
        ),
        "jobType": _safe_str(item.get("employmentType")),
        "companyUrl": _safe_str(
            org.get("sameAs") or org.get("url") if isinstance(org, dict) else None
        ),
        "isUrgent": False,
        "scrapedAt": _now_iso(),
    }


def _parse_card_html(card: str) -> dict | None:
    title_match = re.search(
        r'<(?:h[1-4]|a|span)[^>]*class="[^"]*(?:title|heading|name)[^"]*"[^>]*>(.*?)</(?:h[1-4]|a|span)>',
        card,
        re.DOTALL | re.IGNORECASE,
    )
    if not title_match:
        title_match = re.search(r"<a[^>]*href=\"(/j/[^\"]+)\"[^>]*>(.*?)</a>", card, re.DOTALL)
        if title_match:
            href = title_match.group(1)
            title_text = re.sub(r"<[^>]+>", "", title_match.group(2)).strip()
        else:
            return None
    else:
        title_text = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
        href_match = re.search(r'href="(/j/[^"]+)"', card)
        href = href_match.group(1) if href_match else None

    if not title_text or len(title_text) < 3:
        return None

    if not href:
        href_match = re.search(r'href="(/j/[^"]+)"', card)
        if not href_match:
            href_match = re.search(r'href="(https://www\.iimjobs\.com/j/[^"]+)"', card)
        href = href_match.group(1) if href_match else None

    if not href:
        return None

    job_url = href if href.startswith("http") else f"https://www.iimjobs.com{href}"

    company_match = re.search(
        r'class="[^"]*company[^"]*"[^>]*>(.*?)</',
        card,
        re.DOTALL | re.IGNORECASE,
    )
    company = re.sub(r"<[^>]+>", "", company_match.group(1)).strip() if company_match else None

    loc_match = re.search(
        r'class="[^"]*(?:location|city)[^"]*"[^>]*>(.*?)</',
        card,
        re.DOTALL | re.IGNORECASE,
    )
    location = re.sub(r"<[^>]+>", "", loc_match.group(1)).strip() if loc_match else None

    exp_match = re.search(
        r'class="[^"]*(?:experience|exp)[^"]*"[^>]*>(.*?)</',
        card,
        re.DOTALL | re.IGNORECASE,
    )
    experience = re.sub(r"<[^>]+>", "", exp_match.group(1)).strip() if exp_match else None

    sal_match = re.search(
        r'class="[^"]*(?:salary|ctc|compensation)[^"]*"[^>]*>(.*?)</',
        card,
        re.DOTALL | re.IGNORECASE,
    )
    salary = re.sub(r"<[^>]+>", "", sal_match.group(1)).strip() if sal_match else None

    return {
        "jobTitle": title_text,
        "companyName": _safe_str(company),
        "jobUrl": job_url,
        "location": _safe_str(location),
        "experience": _safe_str(experience),
        "salary": _safe_str(salary),
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
    }
