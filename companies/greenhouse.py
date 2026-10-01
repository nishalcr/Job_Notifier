"""Adapter for Greenhouse job boards via the public boards API (all jobs in one request)."""

from typing import Callable

from companies import json_api
from companies.base import CompanyDefinition
from companies.filters import (
    EXCLUDED_LEVEL_KEYWORDS,
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
)


def greenhouse_company(
    *,
    slug: str,
    display_name: str,
    board: str,
    us_office: Callable[[str], bool] | None = None,
) -> CompanyDefinition:
    """
    Build a company from a Greenhouse board token; keeps US jobs only.

    US is read from the location text, or from office names when us_office is
    given (for boards whose locations are bare city names). Office names need
    the full job payload (content=true).
    """
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
    if us_office:
        api_url += "?content=true"
    board_url = f"https://job-boards.greenhouse.io/{board}"

    async def fetch_page_html(page, runtime_config, url: str) -> str:
        print(f"[{runtime_config.slug}] Loading Greenhouse API: {api_url}")
        response = await page.context.request.get(api_url, timeout=30000)
        if not response.ok:
            raise RuntimeError(f"Greenhouse API request failed with status {response.status}")

        jobs = []
        for posting in (await response.json()).get("jobs") or []:
            location = ((posting.get("location") or {}).get("name") or "").strip()
            if us_office:
                offices = [office.get("name") or "" for office in posting.get("offices") or []]
                if not any(us_office(name) for name in offices):
                    continue
            elif not json_api.is_us_location(location):
                continue
            job_id = str(posting.get("id") or "").strip()
            title = str(posting.get("title") or "").strip()
            if not job_id or not title:
                continue
            jobs.append(
                {
                    "key": job_id,
                    "job_id": job_id,
                    "title": title,
                    "location": json_api.format_locations(location.replace(",", ";").split(";") if us_office else location.split(";")),
                    "posted": str(posting.get("first_published") or "").split("T", 1)[0],
                    "url": posting.get("absolute_url") or f"{board_url}/jobs/{job_id}",
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
