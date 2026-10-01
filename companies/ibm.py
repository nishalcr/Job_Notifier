"""IBM careers via the search API behind ibm.com/careers/search."""

import json
import re

from companies import json_api
from companies.base import CompanyDefinition
from companies.filters import (
    EXCLUDED_LEVEL_KEYWORDS,
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
)

IBM_API_URL = "https://www-api.ibm.com/search/api/v2"
IBM_SEARCH_URL = "https://www.ibm.com/careers/search"
PAGE_SIZE = 30

# field_keyword_05 = country, 08 = category, 18 = experience level, 19 = location.
IBM_FILTERS = [
    {"term": {"field_keyword_05": "United States"}},
    {"terms": {"field_keyword_18": ["Entry Level", "Professional"]}},
]
JOB_ID_RE = re.compile(r"jobId=(\d+)")


async def fetch_page_html(page, runtime_config, url: str) -> str:
    page_num = json_api.page_num_from_url(url)
    print(f"[{runtime_config.slug}] Loading IBM API page {page_num}")
    body = {
        "appId": "careers",
        "scopes": ["careers2"],
        "query": {"bool": {"must": []}},
        "post_filter": {"bool": {"must": IBM_FILTERS}},
        "size": PAGE_SIZE,
        "from": (page_num - 1) * PAGE_SIZE,
        "sort": [{"dcdate": "desc"}],
        "lang": "zz",
        "localeSelector": {},
        "sm": {"query": "", "lang": "zz"},
        "_source": ["_id", "title", "url", "field_keyword_08", "field_keyword_18", "field_keyword_19"],
    }
    response = await page.context.request.post(
        IBM_API_URL,
        headers={"content-type": "application/json"},
        data=json.dumps(body),
        timeout=30000,
    )
    if not response.ok:
        raise RuntimeError(f"IBM API request failed with status {response.status}")
    hits = (await response.json()).get("hits") or {}

    jobs = []
    for hit in hits.get("hits") or []:
        source = hit.get("_source") or {}
        match = JOB_ID_RE.search(source.get("url") or "")
        job_id = match.group(1) if match else str(hit.get("_id") or "")
        title = str(source.get("title") or "").strip()
        if not job_id or not title:
            continue
        jobs.append(
            {
                "key": job_id,
                "job_id": job_id,
                "title": title,
                "team": source.get("field_keyword_08") or "",
                "location": source.get("field_keyword_19") or "",
                "posted": "",
                "url": source.get("url") or IBM_SEARCH_URL,
            }
        )
    total = (hits.get("total") or {}).get("value")
    return json_api.make_payload(jobs, total)


COMPANY = CompanyDefinition(
    slug="ibm",
    display_name="IBM",
    default_search_url=IBM_SEARCH_URL,
    default_max_pages=3,
    default_full_scrape_max_pages=20,
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
