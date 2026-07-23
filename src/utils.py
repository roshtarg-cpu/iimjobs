from __future__ import annotations

import re
from urllib.parse import urlparse


def slugify(text: str) -> str:
    slug = text.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def build_search_query(job_title: str, location: str = "") -> str:
    parts = [job_title.strip()]
    if location:
        parts.append(f"In {location.strip()}")
    return " ".join(parts)


def build_search_url(job_title: str, location: str = "", page: int = 1) -> str:
    slug = slugify(job_title)
    if location:
        loc_slug = slugify(location)
        url = f"https://www.iimjobs.com/search/{slug}-jobs-in-{loc_slug}"
    else:
        url = f"https://www.iimjobs.com/search/{slug}-jobs"
    if page > 1:
        url += f"?page={page}"
    return url


def build_api_url(query: str, page: int = 0) -> str:
    from urllib.parse import quote_plus
    return (
        f"https://gladiator.iimjobs.com/job/search"
        f"?query={quote_plus(query)}&page={page}&posting=0&industry="
    )


def parse_proxy(proxy_url: str | None) -> dict | None:
    if not proxy_url:
        return None
    p = urlparse(proxy_url)
    proxy = {"server": f"{p.scheme}://{p.hostname}:{p.port}"}
    if p.username:
        proxy["username"] = p.username
    if p.password:
        proxy["password"] = p.password
    return proxy
