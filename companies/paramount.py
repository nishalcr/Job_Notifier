"""Paramount careers (SAP SuccessFactors career site) via its search result pages."""

import re

from bs4 import BeautifulSoup

from companies import json_api
from companies.base import CompanyDefinition
from companies.filters import (
    EXCLUDED_LEVEL_KEYWORDS,
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
)

PARAMOUNT_BASE_URL = "https://careers.paramount.com"
PARAMOUNT_SEARCH_URL = (
    f"{PARAMOUNT_BASE_URL}/search/?q=&optionsFacetsDD_department=Technology"
    "&sortColumn=referencedate&sortDirection=desc"
)
PAGE_SIZE = 25  # fixed by the site
JOB_ID_RE = re.compile(r"/(\d+)/?$")
ROW_COUNT_RE = re.compile(r'aria-rowcount="(\d+)"')


def _field(tile, name: str) -> str:
    node = tile.select_one(f".section-field.{name}")
    if node is None:
        return ""
    label = node.select_one(".section-label")
    text = node.get_text(" ", strip=True)
    if label is not None:
        text = text.replace(label.get_text(" ", strip=True), "", 1)
    return " ".join(text.split())


async def fetch_page_html(page, runtime_config, url: str) -> str:
    page_num = json_api.page_num_from_url(url)
    print(f"[{runtime_config.slug}] Loading Paramount results page {page_num}")
    response = await page.context.request.get(
        f"{runtime_config.search_url}&startrow={(page_num - 1) * PAGE_SIZE}", timeout=30000
    )
    if not response.ok:
        raise RuntimeError(f"Paramount search request failed with status {response.status}")
    html = await response.text()
    soup = BeautifulSoup(html, "lxml")

    jobs = []
    for tile in soup.select("li.job-tile"):
        path = tile.get("data-url") or ""
        match = JOB_ID_RE.search(path)
        link = tile.select_one("a.jobTitle-link")
        title = link.get_text(" ", strip=True) if link else ""
        # Location looks like "New York, NY, US, 10036".
        location = _field(tile, "location").removeprefix("Location").strip()
        if not match or not title or ", US" not in location:
            continue
        jobs.append(
            {
                "key": match.group(1),
                "job_id": match.group(1),
                "title": title,
                "location": re.sub(r",\s*US(,\s*\d{5})?$", "", location),
                "posted": _field(tile, "date").removeprefix("Date").strip(),
                "url": f"{PARAMOUNT_BASE_URL}{path}",
            }
        )
    total = ROW_COUNT_RE.search(html)
    return json_api.make_payload(jobs, int(total.group(1)) if total else None)


COMPANY = CompanyDefinition(
    slug="paramount",
    display_name="Paramount",
    default_search_url=PARAMOUNT_SEARCH_URL,
    default_max_pages=2,
    default_full_scrape_max_pages=10,
    wait_selectors=(),
    build_search_url=json_api.build_search_url,
    parse_jobs=json_api.parse_jobs,
    get_total_pages=json_api.total_pages_getter(PAGE_SIZE),
    get_total_results=json_api.get_total_results,
    fetch_page_html=fetch_page_html,
    excluded_role_keywords=EXCLUDED_LEVEL_KEYWORDS,
    excluded_title_phrases=DEFAULT_EXCLUDED_TITLE_PHRASES,
    included_title_keywords=ENGINEERING_TITLE_KEYWORDS,
    # Non-US jobs are dropped client-side, so a page can be empty.
    stop_on_empty_page=False,
)
