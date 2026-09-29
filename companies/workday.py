"""Adapter for Workday career sites (*.myworkdayjobs.com) via their public jobs API."""

import json
from typing import Callable

from companies import json_api
from companies.base import CompanyDefinition
from companies.filters import (
    ABOVE_SENIOR_LEVEL_KEYWORDS,
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
)

PAGE_SIZE = 20  # Workday rejects larger pages.


def is_us_posting(posting: dict) -> bool:
    """
    True if a posting's primary location (the first path segment) is in the US.

    For sites without a country filter. Paths look like "/job/San-Jose-California-US/...",
    "/job/Orlando-FL-USA/...", "/job/US-Arizona-Phoenix/...", "/job/McLean-VA/..." or
    "/job/Austin-Texas-United-States-of-America/...".
    """
    parts = (posting.get("externalPath") or "").split("/")
    segment = parts[2] if len(parts) > 2 else ""
    tokens = segment.split("-")
    if {"US", "USA"} & set(tokens) or "United-States" in segment:
        return True
    # "City-ST" paths, e.g. "/job/McLean-VA/...".
    return len(tokens) > 1 and tokens[-1] in json_api.US_STATE_CODES


def workday_company(
    *,
    slug: str,
    display_name: str,
    host: str,
    tenant: str,
    site: str,
    applied_facets: dict[str, list[str]],
    posting_filter: Callable[[dict], bool] | None = None,
    extra_excluded_title_phrases: tuple[str, ...] = (),
    default_max_pages: int = 3,
    default_full_scrape_max_pages: int = 50,
) -> CompanyDefinition:
    """
    Build a company from Workday facets (IDs come from the site's own filters).

    posting_filter drops raw postings client-side, for filters Workday lacks.
    Results are newest first, so regular runs only need the first pages.
    """
    api_url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    site_url = f"https://{host}/en-US/{site}"

    async def fetch_page_html(page, runtime_config, url: str) -> str:
        page_num = json_api.page_num_from_url(url)
        print(f"[{runtime_config.slug}] Loading Workday API page {page_num}")
        response = await page.context.request.post(
            api_url,
            headers={"content-type": "application/json", "accept": "application/json"},
            data=json.dumps(
                {
                    "appliedFacets": applied_facets,
                    "limit": PAGE_SIZE,
                    "offset": (page_num - 1) * PAGE_SIZE,
                    "searchText": "",
                }
            ),
            timeout=30000,
        )
        if not response.ok:
            raise RuntimeError(f"Workday API request failed with status {response.status}")
        data = await response.json()

        jobs = []
        for posting in data.get("jobPostings") or []:
            if posting_filter and not posting_filter(posting):
                continue
            path = posting.get("externalPath") or ""
            job_id = next(iter(posting.get("bulletFields") or []), "") or path
            if not job_id or not posting.get("title"):
                continue
            jobs.append(
                {
                    "key": job_id,
                    "job_id": job_id,
                    "title": posting["title"].strip(),
                    "location": posting.get("locationsText") or "",
                    "posted": posting.get("postedOn") or "",
                    "url": f"{site_url}{path}",
                }
            )
        # Workday only reports the total on the first page.
        return json_api.make_payload(jobs, data.get("total") if page_num == 1 else None)

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
        # With a client-side filter a page can be empty while later pages still match.
        stop_on_empty_page=posting_filter is None,
    )
