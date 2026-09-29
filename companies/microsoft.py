"""Microsoft careers (Eightfold PCSX) via the search API, called from inside the careers page.

The API only answers requests made with the page's session, so the careers page
is loaded once per run and each results page is fetched from it.
"""

import json
from datetime import datetime, timezone
from urllib.parse import urlencode

from playwright.async_api import TimeoutError as PlaywrightTimeout

from companies import json_api
from companies.base import CompanyDefinition
from companies.filters import (
    ABOVE_SENIOR_LEVEL_KEYWORDS,
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
)

MICROSOFT_BASE_URL = "https://apply.careers.microsoft.com"
MICROSOFT_SEARCH_URL = f"{MICROSOFT_BASE_URL}/careers?domain=microsoft.com"
PAGE_SIZE = 10  # fixed by the API
SEARCH_FILTERS = [
    ("domain", "microsoft.com"),
    ("query", ""),
    ("location", "United States"),
    ("sort_by", "timestamp"),
    ("filter_profession", "software engineering"),
    ("filter_profession", "security engineering"),
    ("filter_profession", "research, applied, & data sciences"),
    ("filter_roletype", "individual contributor"),
    ("filter_employment_type", "full-time"),
]


def _format_location(location: str) -> str:
    """"United States, Washington, Redmond" -> "Redmond, Washington"."""
    parts = [part.strip() for part in location.split(",") if part.strip()]
    if parts and parts[0] == "United States":
        parts = parts[1:]
    return ", ".join(dict.fromkeys(reversed(parts)))


async def _ensure_careers_page(page) -> None:
    if page.url.startswith(MICROSOFT_BASE_URL):
        return
    for attempt in range(1, 3):
        try:
            await page.goto(MICROSOFT_SEARCH_URL, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3000)
            return
        except PlaywrightTimeout:
            if attempt == 2:
                raise


async def fetch_page_html(page, runtime_config, url: str) -> str:
    page_num = json_api.page_num_from_url(url)
    print(f"[{runtime_config.slug}] Loading Microsoft search page {page_num}")
    await _ensure_careers_page(page)
    query = urlencode(SEARCH_FILTERS + [("start", (page_num - 1) * PAGE_SIZE)])
    status, body = await page.evaluate(
        "async (q) => { const r = await fetch('/api/pcsx/search?' + q); return [r.status, await r.text()]; }",
        query,
    )
    if status != 200:
        raise RuntimeError(f"Microsoft search request failed with status {status}")
    data = json.loads(body).get("data") or {}

    jobs = []
    for position in data.get("positions") or []:
        job_id = str(position.get("id") or "").strip()
        title = str(position.get("name") or "").strip()
        if not job_id or not title:
            continue
        posted = position.get("postedTs")
        jobs.append(
            {
                "key": job_id,
                "job_id": position.get("displayJobId") or job_id,
                "title": title,
                "team": position.get("department") or "",
                "location": json_api.format_locations(
                    [_format_location(loc) for loc in position.get("locations") or []]
                ),
                "posted": (
                    datetime.fromtimestamp(posted, tz=timezone.utc).date().isoformat() if posted else ""
                ),
                "url": f"{MICROSOFT_BASE_URL}{position.get('positionUrl') or f'/careers/job/{job_id}'}",
            }
        )
    return json_api.make_payload(jobs, data.get("count"))


COMPANY = CompanyDefinition(
    slug="microsoft",
    display_name="Microsoft",
    default_search_url=MICROSOFT_SEARCH_URL,
    default_max_pages=5,
    default_full_scrape_max_pages=60,
    wait_selectors=(),
    build_search_url=json_api.build_search_url,
    parse_jobs=json_api.parse_jobs,
    get_total_pages=json_api.total_pages_getter(PAGE_SIZE),
    get_total_results=json_api.get_total_results,
    fetch_page_html=fetch_page_html,
    excluded_role_keywords=ABOVE_SENIOR_LEVEL_KEYWORDS,
    excluded_title_phrases=DEFAULT_EXCLUDED_TITLE_PHRASES,
    included_title_keywords=ENGINEERING_TITLE_KEYWORDS,
)
