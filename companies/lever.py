"""Adapter for Lever job boards via the public postings API (all jobs in one request)."""

from datetime import datetime, timezone

from companies import json_api
from companies.base import CompanyDefinition
from companies.filters import (
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
    EXCLUDED_LEVEL_KEYWORDS,
)


def _locations(posting: dict) -> list[str]:
    categories = posting.get("categories") or {}
    return categories.get("allLocations") or [categories.get("location") or ""]


def _is_us(posting: dict) -> bool:
    return posting.get("country") == "US" or any(json_api.is_us_location(loc) for loc in _locations(posting))


def lever_company(*, slug: str, display_name: str, board: str) -> CompanyDefinition:
    """Build a company from a Lever account name; keeps US jobs only."""
    api_url = f"https://api.lever.co/v0/postings/{board}?mode=json"
    board_url = f"https://jobs.lever.co/{board}"

    async def fetch_page_html(page, runtime_config, url: str) -> str:
        print(f"[{runtime_config.slug}] Loading Lever API: {api_url}")
        response = await page.context.request.get(api_url, timeout=30000)
        if not response.ok:
            raise RuntimeError(f"Lever API request failed with status {response.status}")

        jobs = []
        for posting in await response.json():
            if not _is_us(posting):
                continue
            job_id = str(posting.get("id") or "").strip()
            title = str(posting.get("text") or "").strip()
            if not job_id or not title:
                continue
            created = posting.get("createdAt")
            jobs.append(
                {
                    "key": job_id,
                    "job_id": job_id,
                    "title": title,
                    "team": (posting.get("categories") or {}).get("team") or "",
                    "location": json_api.format_locations(_locations(posting)),
                    "posted": (
                        datetime.fromtimestamp(created / 1000, tz=timezone.utc).date().isoformat() if created else ""
                    ),
                    "url": posting.get("hostedUrl") or f"{board_url}/{job_id}",
                }
            )
        return json_api.make_payload(jobs, len(jobs))

    return CompanyDefinition(
        slug=slug,
        display_name=display_name,
        default_search_url=board_url,
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
