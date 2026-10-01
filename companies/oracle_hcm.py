"""Adapter for Oracle Recruiting Cloud career sites (hcmUI CandidateExperience) via their REST API."""

from companies import json_api
from companies.base import CompanyDefinition
from companies.filters import (
    EXCLUDED_LEVEL_KEYWORDS,
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
)

PAGE_SIZE = 25


def oracle_hcm_company(
    *,
    slug: str,
    display_name: str,
    host: str,
    site_number: str,
    location_id: str,
    category_ids: tuple[str, ...],
    default_max_pages: int = 2,
    default_full_scrape_max_pages: int = 40,
) -> CompanyDefinition:
    """Build a company from Oracle facet IDs (location and job categories), newest first."""
    site_url = f"https://{host}/hcmUI/CandidateExperience/en/sites/{site_number}"

    def api_url(page_num: int) -> str:
        finder = ",".join(
            (
                f"findReqs;siteNumber={site_number}",
                f"limit={PAGE_SIZE}",
                f"offset={(page_num - 1) * PAGE_SIZE}",
                "sortBy=POSTING_DATES_DESC",
                f"locationId={location_id}",
            )
            + (("selectedCategoriesFacet=" + "%3B".join(category_ids),) if category_ids else ())
        )
        return (
            f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
            f"?onlyData=true&expand=requisitionList.secondaryLocations&finder={finder}"
        )

    async def fetch_page_html(page, runtime_config, url: str) -> str:
        page_num = json_api.page_num_from_url(url)
        print(f"[{runtime_config.slug}] Loading Oracle API page {page_num}")
        response = await page.context.request.get(
            api_url(page_num), headers={"accept": "application/json"}, timeout=30000
        )
        if not response.ok:
            raise RuntimeError(f"Oracle API request failed with status {response.status}")
        items = (await response.json()).get("items") or [{}]
        result = items[0]

        jobs = []
        for req in result.get("requisitionList") or []:
            job_id = str(req.get("Id") or "").strip()
            title = str(req.get("Title") or "").strip()
            if not job_id or not title:
                continue
            locations = [req.get("PrimaryLocation") or ""] + [
                loc.get("Name") or "" for loc in req.get("secondaryLocations") or []
            ]
            jobs.append(
                {
                    "key": job_id,
                    "job_id": job_id,
                    "title": title,
                    "location": json_api.format_locations(locations),
                    "posted": req.get("PostedDate") or "",
                    "url": f"{site_url}/job/{job_id}",
                }
            )
        return json_api.make_payload(jobs, result.get("TotalJobsCount"))

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
        excluded_role_keywords=EXCLUDED_LEVEL_KEYWORDS,
        excluded_title_phrases=DEFAULT_EXCLUDED_TITLE_PHRASES,
        included_title_keywords=ENGINEERING_TITLE_KEYWORDS,
    )
