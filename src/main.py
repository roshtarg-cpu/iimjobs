from __future__ import annotations

import asyncio
import random

from apify import Actor
from camoufox.async_api import AsyncCamoufox

from .parser import extract_next_data, parse_api_response, parse_jobs_from_html
from .utils import build_api_url, build_search_query, build_search_url, parse_proxy

MAX_RETRIES = 3
BASE_DELAY = 2.0


async def _fetch_api(url: str, proxy_url: str | None) -> dict | None:
    proxy = parse_proxy(proxy_url)
    try:
        async with AsyncCamoufox(
            headless=True,
            proxy=proxy,
            geoip=True,
            firefox_user_prefs={"security.sandbox.content.level": 0},
        ) as browser:
            page = await browser.new_page()
            resp = await page.goto(url, wait_until="networkidle", timeout=90000)
            await page.wait_for_timeout(2000)
            body = await page.content()
            text = body
            import re
            m = re.search(r"<pre[^>]*>(.*?)</pre>", body, re.DOTALL)
            if m:
                text = m.group(1)
            else:
                text = re.sub(r"<[^>]+>", "", body).strip()
            if text:
                import json
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    Actor.log.warning("API response not valid JSON (%d chars)", len(text))
    except Exception as exc:
        Actor.log.warning("API fetch failed: %s", exc)
    return None


async def _fetch_html(url: str, proxy_url: str | None) -> str | None:
    proxy = parse_proxy(proxy_url)
    try:
        async with AsyncCamoufox(
            headless=True,
            proxy=proxy,
            geoip=True,
            firefox_user_prefs={"security.sandbox.content.level": 0},
        ) as browser:
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=90000)
            await page.wait_for_timeout(3000)
            html = await page.content()
            if len(html) > 500:
                return html
            Actor.log.warning("Short response (%d bytes)", len(html))
    except Exception as exc:
        Actor.log.warning("HTML fetch failed: %s", exc)
    return None


async def _fetch_with_retry(fetch_fn, url: str, proxy_url: str | None):
    for attempt in range(1, MAX_RETRIES + 1):
        Actor.log.info("Fetching %s (attempt %d/%d)", url, attempt, MAX_RETRIES)
        result = await fetch_fn(url, proxy_url)
        if result:
            return result
        if attempt < MAX_RETRIES:
            wait = BASE_DELAY * attempt + random.uniform(1, 3)
            Actor.log.info("Retrying in %.1f seconds...", wait)
            await asyncio.sleep(wait)
    Actor.log.error("All %d attempts failed for %s", MAX_RETRIES, url)
    return None


async def _scrape_via_api(
    query: str, proxy_url: str | None, max_results: int
) -> int:
    total_pushed = 0
    page = 0
    seen_urls: set[str] = set()

    while total_pushed < max_results:
        url = build_api_url(query, page)
        data = await _fetch_with_retry(_fetch_api, url, proxy_url)

        if not data:
            Actor.log.error("API fetch failed on page %d, stopping", page)
            return total_pushed

        jobs, has_more = parse_api_response(data)
        Actor.log.info("API page %d: found %d jobs (hasMore=%s)", page, len(jobs), has_more)

        if not jobs:
            break

        new_count = 0
        for job in jobs:
            if total_pushed >= max_results:
                break
            job_url = job.get("jobUrl", "")
            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)
            await Actor.push_data(job)
            total_pushed += 1
            new_count += 1
            if total_pushed % 10 == 0:
                Actor.log.info("Progress: %d/%d jobs scraped", total_pushed, max_results)

        if new_count == 0 or not has_more:
            break

        page += 1
        delay = random.uniform(BASE_DELAY, BASE_DELAY + 3)
        Actor.log.info("Waiting %.1f seconds before next page...", delay)
        await asyncio.sleep(delay)

    return total_pushed


async def _scrape_via_html(
    job_title: str, location: str, proxy_url: str | None, max_results: int
) -> int:
    total_pushed = 0
    page = 1
    seen_urls: set[str] = set()
    consecutive_empty = 0

    while total_pushed < max_results:
        url = build_search_url(job_title, location, page)
        html = await _fetch_with_retry(_fetch_html, url, proxy_url)

        if not html:
            Actor.log.error("HTML fetch failed on page %d, stopping", page)
            break

        jobs = parse_jobs_from_html(html)
        Actor.log.info("HTML page %d: found %d jobs", page, len(jobs))

        if not jobs:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                break
            page += 1
            await asyncio.sleep(random.uniform(BASE_DELAY, BASE_DELAY + 2))
            continue

        consecutive_empty = 0
        new_count = 0
        for job in jobs:
            if total_pushed >= max_results:
                break
            job_url = job.get("jobUrl", "")
            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)
            await Actor.push_data(job)
            total_pushed += 1
            new_count += 1
            if total_pushed % 10 == 0:
                Actor.log.info("Progress: %d/%d jobs scraped", total_pushed, max_results)

        if new_count == 0:
            break

        page += 1
        delay = random.uniform(BASE_DELAY, BASE_DELAY + 3)
        await asyncio.sleep(delay)

    return total_pushed


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        job_title = actor_input.get("jobTitle")
        location = actor_input.get("location", "")
        max_results = actor_input.get("maxResults", 50)

        if not job_title:
            raise ValueError("jobTitle is required")

        Actor.log.info(
            "Starting IIMJobs scraper — title=%r, location=%r, maxResults=%d",
            job_title, location, max_results,
        )

        proxy_cfg = await Actor.create_proxy_configuration(
            actor_proxy_input=actor_input.get("proxyConfiguration"),
        )
        proxy_url = await proxy_cfg.new_url() if proxy_cfg else None

        query = build_search_query(job_title, location)
        Actor.log.info("Trying API endpoint (gladiator.iimjobs.com)...")
        total = await _scrape_via_api(query, proxy_url, max_results)

        if total == 0:
            Actor.log.info("API returned no results, falling back to HTML scraping...")
            total = await _scrape_via_html(job_title, location, proxy_url, max_results)

        Actor.log.info("Scraping complete. Total jobs scraped: %d", total)
