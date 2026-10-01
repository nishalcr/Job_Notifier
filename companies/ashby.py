"""Adapter for Ashby job boards via the public posting API (all jobs in one request)."""

from companies import json_api
from companies.base import CompanyDefinition
from companies.filters import (
    EXCLUDED_LEVEL_KEYWORDS,
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
)


def _is_us(job: dict) -> bool:
    country = (((job.get("address") or {}).get("postalAddress") or {}).get("addressCountry") or "").strip()
    if country in ("United States", "USA", "US"):
        return True
    locations = [job.get("location") or ""] + [
        (loc.get("location") if isinstance(loc, dict) else loc) or "" for loc in job.get("secondaryLocations") or []
    ]
    # Ashby location names often look like "US-CA-Menlo Park" or "US, Remote".
    return any(loc.startswith(("US-", "US,", "US ")) or json_api.is_us_location(loc) for loc in locations)


def ashby_company(*, slug: str, display_name: str, board: str) -> CompanyDefinition:
    """Build a company from an Ashby job board name; keeps listed US jobs only."""
    api_url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
    board_url = f"https://jobs.ashbyhq.com/{board}"

    async def fetch_page_html(page, runtime_config, url: str) -> str:
        print(f"[{runtime_config.slug}] Loading Ashby API: {api_url}")
        response = await page.context.request.get(api_url, timeout=30000)
        if not response.ok:
            raise RuntimeError(f"Ashby API request failed with status {response.status}")

        jobs = []
        for job in (await response.json()).get("jobs") or []:
            if job.get("isListed") is False or not _is_us(job):
                continue
            job_id = str(job.get("id") or "").strip()
            title = str(job.get("title") or "").strip()
            if not job_id or not title:
                continue
            secondary = [
                (loc.get("location") if isinstance(loc, dict) else loc) or "" for loc in job.get("secondaryLocations") or []
            ]
            jobs.append(
                {
                    "key": job_id,
                    "job_id": job_id,
                    "title": title,
                    "team": job.get("team") or job.get("department") or "",
                    "location": json_api.format_locations([job.get("location") or ""] + secondary),
                    "posted": str(job.get("publishedAt") or "").split("T", 1)[0],
                    "url": job.get("jobUrl") or f"{board_url}/{job_id}",
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
