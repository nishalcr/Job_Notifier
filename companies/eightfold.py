"""Adapter for Eightfold AI career sites (e.g. explore.jobs.netflix.net) via their public jobs API."""

from companies import json_api
from companies.base import CompanyDefinition
from companies.filters import (
    ABOVE_SENIOR_LEVEL_KEYWORDS,
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
)

PAGE_SIZE = 10  # fixed by the API


def eightfold_company(
    *,
    slug: str,
    display_name: str,
    host: str,
    domain: str,
    extra_excluded_title_phrases: tuple[str, ...] = (),
    default_max_pages: int = 3,
    default_full_scrape_max_pages: int = 40,
) -> CompanyDefinition:
    """Build a company from an Eightfold host and company domain; US jobs, newest first."""
    api_url = f"https://{host}/api/apply/v2/jobs"
    site_url = f"https://{host}/careers"

    async def fetch_page_html(page, runtime_config, url: str) -> str:
        page_num = json_api.page_num_from_url(url)
        print(f"[{runtime_config.slug}] Loading Eightfold API page {page_num}")
        response = await page.context.request.get(
            api_url,
            params={
                "domain": domain,
                "start": (page_num - 1) * PAGE_SIZE,
                "num": PAGE_SIZE,
                "location": "United States",
                "sort_by": "new",
            },
            timeout=30000,
        )
        if not response.ok:
            raise RuntimeError(f"Eightfold API request failed with status {response.status}")
        data = await response.json()

        jobs = []
        for position in data.get("positions") or []:
            job_id = str(position.get("id") or "").strip()
            title = str(position.get("name") or "").strip()
            if not job_id or not title:
                continue
            jobs.append(
                {
                    "key": job_id,
                    "job_id": position.get("display_job_id") or job_id,
                    "title": title,
                    "team": position.get("department") or "",
                    "location": position.get("location") or "",
                    "posted": "",
                    "url": position.get("canonicalPositionUrl") or f"{site_url}/job/{job_id}",
                }
            )
        return json_api.make_payload(jobs, data.get("count"))

    return CompanyDefinition(
        slug=slug,
        display_name=display_name,
        default_search_url=site_url,
        default_max_pages=default_max_pages,
        default_full_scrape_max_pages=default_full_scrape_max_pages,
        wait_selectors=(),
        build_search_url=json_api.build_search_url,
        parse_jobs=json_api.parse_jobs,
        get_total_pages=json_api.total_pages_getter(PAGE_SIZE),
        get_total_results=json_api.get_total_results,
        fetch_page_html=fetch_page_html,
        excluded_role_keywords=ABOVE_SENIOR_LEVEL_KEYWORDS,
        excluded_title_phrases=DEFAULT_EXCLUDED_TITLE_PHRASES + extra_excluded_title_phrases,
        included_title_keywords=ENGINEERING_TITLE_KEYWORDS,
    )
