import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from companies import json_api
from companies.base import CompanyDefinition
from companies.filters import (
    EXCLUDED_LEVEL_KEYWORDS,
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
)

APPLE_SEARCH_URL = (
    "https://jobs.apple.com/en-us/search"
        "?location=united-states-USA"
    "&team=apps-and-frameworks-SFTWR-AF+cloud-and-infrastructure-SFTWR-CLD"
    "+core-operating-systems-SFTWR-COS+devops-and-site-reliability-SFTWR-DSR"
    "+engineering-project-management-SFTWR-EPM"
    "+information-systems-and-technology-SFTWR-ISTECH"
    "+machine-learning-and-ai-SFTWR-MCHLN+security-and-privacy-SFTWR-SEC"
    "+software-quality-automation-and-tools-SFTWR-SQAT"
    "+wireless-software-SFTWR-WSFT"
)

EXCLUDED_ROLE_KEYWORDS = EXCLUDED_LEVEL_KEYWORDS
EXCLUDED_TITLE_PHRASES = DEFAULT_EXCLUDED_TITLE_PHRASES
PAGE_SIZE = 20

# The search page embeds its results as JSON, so no rendering is needed (rendering
# sometimes came back without the job list).
_HYDRATION_RE = re.compile(r"__staticRouterHydrationData = JSON\.parse\((\".*?\")\);", re.S)


async def fetch_page_html(page, runtime_config, url: str) -> str:
    print(f"[{runtime_config.slug}] Loading search page data: {url}")
    response = await page.context.request.get(url, timeout=30000)
    if not response.ok:
        raise RuntimeError(f"Apple search request failed with status {response.status}")
    match = _HYDRATION_RE.search(await response.text())
    if not match:
        raise RuntimeError("Apple search page has no embedded results data")
    search = json.loads(json.loads(match.group(1)))["loaderData"]["search"]

    jobs = []
    for role in search.get("searchResults") or []:
        job_id = str(role.get("id") or "").strip()
        title = str(role.get("postingTitle") or "").strip()
        if not job_id or not title:
            continue
        team = role.get("team") or {}
        slug = role.get("transformedPostingTitle") or ""
        jobs.append(
            {
                "key": job_id,
                "job_id": job_id,
                "title": title,
                "team": team.get("teamName") or "",
                "location": json_api.format_locations([loc.get("name") or "" for loc in role.get("locations") or []]),
                "posted": str(role.get("postDateInGMT") or "")[:10] or role.get("postingDate") or "",
                "url": f"https://jobs.apple.com/en-us/details/{job_id}/{slug}?team={team.get('teamCode') or ''}",
            }
        )
    return json_api.make_payload(jobs, search.get("totalRecords"))


def build_search_url(search_url: str, page_num: int) -> str:
    parsed = urlsplit(search_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params["page"] = str(page_num)
    return urlunsplit(parsed._replace(query=urlencode(params, doseq=True)))


COMPANY = CompanyDefinition(
    slug="apple",
    display_name="Apple",
    default_search_url=APPLE_SEARCH_URL,
    default_max_pages=2,
    default_full_scrape_max_pages=150,
    wait_selectors=(),
    build_search_url=build_search_url,
    parse_jobs=json_api.parse_jobs,
    get_total_pages=json_api.total_pages_getter(PAGE_SIZE),
    get_total_results=json_api.get_total_results,
    fetch_page_html=fetch_page_html,
    excluded_role_keywords=EXCLUDED_ROLE_KEYWORDS,
    excluded_title_phrases=EXCLUDED_TITLE_PHRASES,
    included_title_keywords=ENGINEERING_TITLE_KEYWORDS,
    page_concurrency=4,
)