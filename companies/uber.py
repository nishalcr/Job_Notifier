import json
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from playwright.async_api import TimeoutError as PlaywrightTimeout

from companies.base import CompanyDefinition
from companies.filters import (
    ABOVE_SENIOR_LEVEL_KEYWORDS,
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
)
from uber_parser import get_total_pages, get_total_results, parse_jobs

# Uber moved careers to jobs.uber.com (Cloudflare-protected). The search API only
# honours `team` and `page`, so the US-only filter is applied client-side.
UBER_JOBS_SITE_URL = "https://jobs.uber.com/en/jobs/"
UBER_SEARCH_API_PATH = "/api/jobs/search/"
UBER_SEARCH_URL = f"{UBER_JOBS_SITE_URL}?team=Engineer"

UBER_COUNTRY = "united states"

EXCLUDED_ROLE_KEYWORDS = ABOVE_SENIOR_LEVEL_KEYWORDS
EXCLUDED_TITLE_PHRASES = DEFAULT_EXCLUDED_TITLE_PHRASES


RESULTS_PER_PAGE = 10
MAX_API_PAGES = 100
_FILTERED_JOBS_CACHE: dict[str, list[dict]] = {}


def build_search_url(search_url: str, page_num: int) -> str:
    parsed = urlsplit(search_url)
    return urlunsplit(parsed._replace(fragment=f"page={page_num}"))


def _page_num_from_url(url: str) -> int:
    fragment = urlsplit(url).fragment
    if fragment.startswith("page="):
        try:
            return max(1, int(fragment.split("=", 1)[1]))
        except ValueError:
            return 1
    return 1


def _api_query(search_url: str, page_num: int) -> str:
    params = parse_qs(urlsplit(search_url).query)
    query = [("team", team) for team in params.get("team", [])]
    query.append(("page", str(page_num)))
    return f"{UBER_SEARCH_API_PATH}?{urlencode(query)}"


def _matches_location(raw_job: dict) -> bool:
    for location in raw_job.get("Locations") or []:
        if not isinstance(location, dict):
            continue
        if str(location.get("Country") or "").strip().lower() == UBER_COUNTRY:
            return True
    return False


async def _open_jobs_site(page, runtime_config) -> None:
    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        try:
            await page.goto(UBER_JOBS_SITE_URL, wait_until="domcontentloaded", timeout=45000)
            break
        except PlaywrightTimeout:
            if attempt == max_attempts:
                raise
            await page.wait_for_timeout(2000)

    # Give the Cloudflare challenge time to clear before calling the API.
    for selector in runtime_config.definition.wait_selectors:
        try:
            await page.wait_for_selector(selector, timeout=15000)
            break
        except PlaywrightTimeout:
            continue


async def _fetch_api_page(page, runtime_config, page_num: int) -> dict:
    query = _api_query(runtime_config.search_url, page_num)
    for attempt in range(1, 3):
        status, body = await page.evaluate(
            "async (q) => { const r = await fetch(q, {headers: {accept: 'application/json'}});"
            " return [r.status, await r.text()]; }",
            query,
        )
        if status == 200:
            return json.loads(body)
        if attempt == 1:
            await _open_jobs_site(page, runtime_config)
    raise RuntimeError(f"Uber API request failed with status {status}")


async def _build_filtered_jobs_cache(page, runtime_config) -> list[dict]:
    cache_key = runtime_config.search_url
    if cache_key in _FILTERED_JOBS_CACHE:
        return _FILTERED_JOBS_CACHE[cache_key]

    await _open_jobs_site(page, runtime_config)
    first_page = await _fetch_api_page(page, runtime_config, 1)
    total_pages = min(MAX_API_PAGES, max(1, int(first_page.get("totalPages") or 1)))

    filtered_jobs = []
    seen_ids = set()
    for api_page_num in range(1, total_pages + 1):
        data = first_page if api_page_num == 1 else await _fetch_api_page(page, runtime_config, api_page_num)
        for raw_job in data.get("jobs") or []:
            job_id = str(raw_job.get("Id") or "").strip()
            if not job_id or job_id in seen_ids or not _matches_location(raw_job):
                continue
            seen_ids.add(job_id)
            filtered_jobs.append(raw_job)

    _FILTERED_JOBS_CACHE[cache_key] = filtered_jobs
    print(
        f"[{runtime_config.slug}] Filtered {len(filtered_jobs)} matching jobs "
        f"from {first_page.get('totalJobs', 'unknown')} raw Uber listings."
    )
    return filtered_jobs


def _build_filtered_results_payload(filtered_jobs: list[dict], page_num: int) -> str:
    start_index = max(0, page_num - 1) * RESULTS_PER_PAGE
    page_jobs = filtered_jobs[start_index : start_index + RESULTS_PER_PAGE]
    return json.dumps(
        {
            "data": {
                "results": page_jobs,
                "totalResults": {"low": len(filtered_jobs)},
            },
        }
    )


async def fetch_page_html(page, runtime_config, url: str) -> str:
    page_num = _page_num_from_url(url)
    print(f"[{runtime_config.slug}] Loading filtered page {page_num} from {UBER_JOBS_SITE_URL}")
    filtered_jobs = await _build_filtered_jobs_cache(page, runtime_config)
    return _build_filtered_results_payload(filtered_jobs, page_num)


COMPANY = CompanyDefinition(
    slug="uber",
    display_name="Uber",
    default_search_url=UBER_SEARCH_URL,
    # The Uber API is not sorted by recency, so regular runs cover the full filtered set.
    default_max_pages=50,
    default_full_scrape_max_pages=50,
    wait_selectors=(
        'a[href*="/en/jobs/"]',
        'text=Search jobs',
    ),
    build_search_url=build_search_url,
    parse_jobs=parse_jobs,
    get_total_pages=get_total_pages,
    get_total_results=get_total_results,
    fetch_page_html=fetch_page_html,
    excluded_role_keywords=EXCLUDED_ROLE_KEYWORDS,
    excluded_title_phrases=EXCLUDED_TITLE_PHRASES,
    included_title_keywords=ENGINEERING_TITLE_KEYWORDS,
)
