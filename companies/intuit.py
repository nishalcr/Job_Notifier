"""Intuit: jobs.intuit.com (Radancy TalentBrew) search results, filtered to the US."""

import html
import re
from urllib.parse import urlencode

from companies import json_api
from companies.base import CompanyDefinition
from companies.filters import (
    EXCLUDED_LEVEL_KEYWORDS,
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
)

BASE_URL = "https://jobs.intuit.com"
PAGE_SIZE = 100
# Country facet: United States (GeoNames ID).
US_FACET = {
    "FacetFilters[0].ID": "6252001",
    "FacetFilters[0].FacetType": "2",
    "FacetFilters[0].Display": "United States",
    "FacetFilters[0].IsApplied": "true",
    "FacetFilters[0].FieldName": "",
}


def _results_url(page_num: int) -> str:
    params = {
        "CurrentPage": page_num,
        "RecordsPerPage": PAGE_SIZE,
        "SearchResultsModuleName": "Search Results",
        "SearchFiltersModuleName": "Search Filters",
        "SearchType": 5,
        **US_FACET,
    }
    return f"{BASE_URL}/search-jobs/results?{urlencode(params)}"


def _location(tile: str, path: str) -> str:
    match = re.search(r'<span class="job-location">([^<]*)</span>', tile)
    location = html.unescape(match.group(1)).strip() if match else ""
    if location and location != "Multiple Locations":
        return location
    # "/job/mountain-view/<title>/..." -> "Mountain View; +more"
    city = path.split("/")[2].replace("-", " ").title() if path.count("/") > 2 else ""
    return f"{city}; +more" if location == "Multiple Locations" and city else city or location


async def fetch_page_html(page, runtime_config, url: str) -> str:
    page_num = json_api.page_num_from_url(url)
    print(f"[{runtime_config.slug}] Loading Intuit results page {page_num}")
    response = await page.context.request.get(
        _results_url(page_num),
        headers={"X-Requested-With": "XMLHttpRequest"},
        timeout=30000,
    )
    if not response.ok:
        raise RuntimeError(f"Intuit search request failed with status {response.status}")
    results = (await response.json()).get("results") or ""

    jobs = []
    for tile in results.split("<li data-remote=")[1:]:
        link = re.search(r'<a href="(/job/[^"]+)"', tile)
        title = re.search(r"<h2>([^<]*)</h2>", tile)
        job_id = re.search(r'data-job-id="(\d{6,})"', tile)
        if not (link and title and job_id):
            continue
        jobs.append(
            {
                "key": job_id.group(1),
                "job_id": job_id.group(1),
                "title": html.unescape(title.group(1)).strip(),
                "location": _location(tile, link.group(1)),
                "posted": "",
                "url": f"{BASE_URL}{link.group(1)}",
            }
        )
    total = re.search(r'data-total-results="(\d+)"', results)
    return json_api.make_payload(jobs, int(total.group(1)) if total else None)


COMPANY = CompanyDefinition(
    slug="intuit",
    display_name="Intuit",
    default_search_url=f"{BASE_URL}/search-jobs",
    # Results are not sorted by date, so every page is read (about 550 US jobs).
    default_max_pages=8,
    default_full_scrape_max_pages=8,
    wait_selectors=(),
    build_search_url=json_api.build_search_url,
    parse_jobs=json_api.parse_jobs,
    get_total_pages=json_api.total_pages_getter(PAGE_SIZE),
    get_total_results=json_api.get_total_results,
    fetch_page_html=fetch_page_html,
    excluded_role_keywords=EXCLUDED_LEVEL_KEYWORDS,
    excluded_title_phrases=DEFAULT_EXCLUDED_TITLE_PHRASES,
    included_title_keywords=ENGINEERING_TITLE_KEYWORDS,
    page_concurrency=4,
)
