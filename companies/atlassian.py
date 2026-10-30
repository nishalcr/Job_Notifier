"""Atlassian: its careers site serves every open job in one JSON list."""

from companies import json_api
from companies.base import CompanyDefinition
from companies.filters import (
    EXCLUDED_LEVEL_KEYWORDS,
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
)

API_URL = "https://www.atlassian.com/endpoint/careers/listings"
SITE_URL = "https://www.atlassian.com/company/careers/all-jobs"


def _clean_location(location: str) -> str:
    """"Seattle - United States -   Seattle, Washington  United States" -> "Seattle, United States"."""
    parts = [part.strip() for part in location.split(" - ")]
    return ", ".join(parts[:2]) if len(parts) >= 2 else location.strip()


async def fetch_page_html(page, runtime_config, url: str) -> str:
    print(f"[{runtime_config.slug}] Loading Atlassian listings: {API_URL}")
    response = await page.context.request.get(API_URL, timeout=30000)
    if not response.ok:
        raise RuntimeError(f"Atlassian listings request failed with status {response.status}")

    jobs = []
    for posting in await response.json():
        locations = [loc for loc in posting.get("locations") or [] if "United States" in loc]
        if not locations:
            continue
        job_id = str(posting.get("id") or "").strip()
        title = str(posting.get("title") or "").strip()
        if not job_id or not title:
            continue
        portal = posting.get("portalJobPost") or {}
        jobs.append(
            {
                "key": job_id,
                "job_id": job_id,
                "title": title,
                "team": posting.get("category") or "",
                "location": json_api.format_locations([_clean_location(loc) for loc in locations]),
                "posted": "",
                "url": portal.get("portalUrl") or posting.get("applyUrl") or SITE_URL,
            }
        )
    return json_api.make_payload(jobs, len(jobs))


COMPANY = CompanyDefinition(
    slug="atlassian",
    display_name="Atlassian",
    default_search_url=SITE_URL,
    default_max_pages=1,
    default_full_scrape_max_pages=1,
    wait_selectors=(),
    build_search_url=json_api.build_search_url,
    parse_jobs=json_api.parse_jobs,
    get_total_pages=lambda payload: 1,
    get_total_results=json_api.get_total_results,
    fetch_page_html=fetch_page_html,
    excluded_role_keywords=EXCLUDED_LEVEL_KEYWORDS,
    excluded_title_phrases=DEFAULT_EXCLUDED_TITLE_PHRASES,
    included_title_keywords=ENGINEERING_TITLE_KEYWORDS,
)
