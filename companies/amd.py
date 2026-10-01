"""AMD careers (iCIMS / Jibe) via the careers.amd.com jobs API."""

from companies import json_api
from companies.base import CompanyDefinition
from companies.filters import (
    EXCLUDED_LEVEL_KEYWORDS,
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
)

AMD_API_URL = "https://careers.amd.com/api/jobs"
AMD_SEARCH_URL = "https://careers.amd.com/careers-home/jobs"
PAGE_SIZE = 10  # fixed by the API


async def fetch_page_html(page, runtime_config, url: str) -> str:
    page_num = json_api.page_num_from_url(url)
    print(f"[{runtime_config.slug}] Loading AMD API page {page_num}")
    response = await page.context.request.get(
        AMD_API_URL,
        params={
            "page": page_num,
            "sortBy": "posted_date",
            "descending": "true",
            "internal": "false",
            "country": "United States",
            "categories": "Engineering",
        },
        timeout=30000,
    )
    if not response.ok:
        raise RuntimeError(f"AMD API request failed with status {response.status}")
    data = await response.json()

    jobs = []
    for item in data.get("jobs") or []:
        job = item.get("data") or item
        job_id = str(job.get("req_id") or job.get("slug") or "").strip()
        title = str(job.get("title") or "").strip()
        if not job_id or not title:
            continue
        city, state = job.get("city") or "", job.get("state") or ""
        jobs.append(
            {
                "key": job_id,
                "job_id": job_id,
                "title": title,
                "location": ", ".join(part for part in (city, state) if part),
                "posted": str(job.get("posted_date") or "").split("T", 1)[0],
                "url": f"{AMD_SEARCH_URL}/{job.get('slug') or job_id}",
            }
        )
    return json_api.make_payload(jobs, data.get("totalCount"))


COMPANY = CompanyDefinition(
    slug="amd",
    display_name="AMD",
    default_search_url=AMD_SEARCH_URL,
    default_max_pages=4,
    default_full_scrape_max_pages=60,
    wait_selectors=(),
    build_search_url=json_api.build_search_url,
    parse_jobs=json_api.parse_jobs,
    get_total_pages=json_api.total_pages_getter(PAGE_SIZE),
    get_total_results=json_api.get_total_results,
    fetch_page_html=fetch_page_html,
    excluded_role_keywords=EXCLUDED_LEVEL_KEYWORDS,
    excluded_title_phrases=DEFAULT_EXCLUDED_TITLE_PHRASES,
    included_title_keywords=ENGINEERING_TITLE_KEYWORDS,
)
