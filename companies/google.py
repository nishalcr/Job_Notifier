from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from companies.base import CompanyDefinition
from companies.filters import (
    EXCLUDED_LEVEL_KEYWORDS,
    DEFAULT_EXCLUDED_TITLE_PHRASES,
    ENGINEERING_TITLE_KEYWORDS,
)
from google_parser import get_total_pages, get_total_results, parse_jobs

GOOGLE_SEARCH_URL = (
    "https://www.google.com/about/careers/applications/jobs/results/"
    "?location=United%20States"
    "&target_level=MID"
    "&target_level=EARLY"
    "&target_level=ADVANCED"
    "&employment_type=FULL_TIME"
    "&sort_by=date"
)

EXCLUDED_ROLE_KEYWORDS = EXCLUDED_LEVEL_KEYWORDS
EXCLUDED_TITLE_PHRASES = DEFAULT_EXCLUDED_TITLE_PHRASES



def build_search_url(search_url: str, page_num: int) -> str:
    parsed = urlsplit(search_url)
    params = parse_qsl(parsed.query, keep_blank_values=True)
    filtered_params = [(key, value) for key, value in params if key != "page"]
    filtered_params.append(("page", str(page_num)))
    return urlunsplit(parsed._replace(query=urlencode(filtered_params, doseq=True)))


COMPANY = CompanyDefinition(
    slug="google",
    display_name="Google",
    default_search_url=GOOGLE_SEARCH_URL,
    default_max_pages=5,
    default_full_scrape_max_pages=25,
    wait_selectors=(
        'a[href*="/about/careers/applications/jobs/results/"]',
        'text=Jobs search results',
        'text=jobs matched',
    ),
    build_search_url=build_search_url,
    parse_jobs=parse_jobs,
    get_total_pages=get_total_pages,
    get_total_results=get_total_results,
    excluded_role_keywords=EXCLUDED_ROLE_KEYWORDS,
    excluded_title_phrases=EXCLUDED_TITLE_PHRASES,
    included_title_keywords=ENGINEERING_TITLE_KEYWORDS,
)
