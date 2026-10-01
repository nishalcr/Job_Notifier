"""Amazon jobs via the amazon.jobs search JSON endpoint (newest first).

The HTML search page only renders a fraction of results for multi-category
searches, so the JSON endpoint behind it is used instead.
"""

import re

from companies import json_api
from companies.base import CompanyDefinition
from companies.filters import (
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
    EXCLUDED_LEVEL_KEYWORDS,
)

AMAZON_BASE_URL = "https://www.amazon.jobs"
AMAZON_API_URL = f"{AMAZON_BASE_URL}/en/search.json"
AMAZON_SEARCH_URL = f"{AMAZON_BASE_URL}/en/search"
PAGE_SIZE = 50
CATEGORIES = (
    "software-development",
    "machine-learning-science",
    "systems-quality-security-engineering",
    "data-science",
    "business-intelligence",
    "research-science",
)


async def fetch_page_html(page, runtime_config, url: str) -> str:
    page_num = json_api.page_num_from_url(url)
    print(f"[{runtime_config.slug}] Loading Amazon API page {page_num}")
    params = [
        ("offset", str((page_num - 1) * PAGE_SIZE)),
        ("result_limit", str(PAGE_SIZE)),
        ("sort", "recent"),
        ("normalized_country_code[]", "USA"),
        ("job_type[]", "Full-Time"),
        ("is_manager[]", "0"),
    ] + [("category[]", category) for category in CATEGORIES]
    query = "&".join(f"{key}={value}" for key, value in params)
    response = await page.context.request.get(f"{AMAZON_API_URL}?{query}", timeout=30000)
    if not response.ok:
        raise RuntimeError(f"Amazon API request failed with status {response.status}")
    data = await response.json()

    jobs = []
    for job in data.get("jobs") or []:
        job_id = str(job.get("id_icims") or "").strip()
        title = str(job.get("title") or "").strip()
        if not job_id or not title:
            continue
        jobs.append(
            {
                "key": job_id,
                "job_id": job_id,
                "title": title,
                "location": re.sub(r",\s*USA$", "", job.get("normalized_location") or job.get("location") or ""),
                "posted": " ".join(str(job.get("posted_date") or "").split()),
                "url": f"{AMAZON_BASE_URL}{job.get('job_path') or f'/en/jobs/{job_id}'}",
            }
        )
    return json_api.make_payload(jobs, data.get("hits"))


COMPANY = CompanyDefinition(
    slug="amazon",
    display_name="Amazon",
    default_search_url=AMAZON_SEARCH_URL,
    default_max_pages=2,
    default_full_scrape_max_pages=40,
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
