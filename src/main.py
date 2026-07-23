from __future__ import annotations

import asyncio
import random

from apify import Actor
from camoufox.async_api import AsyncCamoufox

from .parser import extract_next_data, parse_jobs_from_html, parse_jobs_from_next_data
from .utils import build_search_url, parse_proxy

MAX_RETRIES = 3
BASE_DELAY = 2.0


async def _fetch(url: str, proxy_url: str | None) -> str | None:
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
        Actor.log.warning("Fetch failed: %s", exc)
    return None


async def _fetch_with_retry(url: str, proxy_url: str | None) -> str | None:
    for attempt in range(1, MAX_RETRIES + 1):
        Actor.log.info("Fetching %s (attempt %d/%d)", url, attempt, MAX_RETRIES)
        html = await _fetch(url, proxy_url)
        if html:
            return html
        if attempt < MAX_RETRIES:
            wait = BASE_DELAY * attempt + random.uniform(1, 3)
            Actor.log.info("Retrying in %.1f seconds...", wait)
            await asyncio.sleep(wait)
    Actor.log.error("All %d attempts failed for %s", MAX_RETRIES, url)
    return None


def _extract_jobs(html: str) -> list[dict]:
    next_data = extract_next_data(html)
    if next_data:
        Actor.log.info("Found __NEXT_DATA__, extracting jobs from JSON")
        jobs = parse_jobs_from_next_data(next_data)
        if jobs:
            return jobs
        Actor.log.info("No jobs in __NEXT_DATA__, falling back to HTML parsing")

    return parse_jobs_from_html(html)


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
            job_title,
            location,
            max_results,
        )

        proxy_cfg = await Actor.create_proxy_configuration(
            actor_proxy_input=actor_input.get("proxyConfiguration"),
        )
        proxy_url = await proxy_cfg.new_url() if proxy_cfg else None

        total_pushed = 0
        page = 1
        seen_urls: set[str] = set()
        consecutive_empty = 0

        while total_pushed < max_results:
            url = build_search_url(job_title, location, page)
            html = await _fetch_with_retry(url, proxy_url)

            if not html:
                Actor.log.error("Failed to fetch page %d, stopping", page)
                break

            jobs = _extract_jobs(html)
            Actor.log.info("Page %d: found %d job listings", page, len(jobs))

            if not jobs:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    Actor.log.info("Two consecutive empty pages, stopping")
                    break
                page += 1
                await asyncio.sleep(random.uniform(BASE_DELAY, BASE_DELAY + 2))
                continue

            consecutive_empty = 0
            new_jobs = 0

            for job in jobs:
                if total_pushed >= max_results:
                    break

                job_url = job.get("jobUrl", "")
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                await Actor.push_data(job)
                total_pushed += 1
                new_jobs += 1

                if total_pushed % 10 == 0:
                    Actor.log.info("Progress: %d/%d jobs scraped", total_pushed, max_results)

            if new_jobs == 0:
                Actor.log.info("No new jobs on page %d, stopping", page)
                break

            page += 1
            delay = random.uniform(BASE_DELAY, BASE_DELAY + 3)
            Actor.log.info("Waiting %.1f seconds before next page...", delay)
            await asyncio.sleep(delay)

        Actor.log.info("Scraping complete. Total jobs scraped: %d", total_pushed)
