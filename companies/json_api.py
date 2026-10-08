"""Helpers for adapters that read a JSON jobs API instead of rendering HTML.

The adapter's fetch_page_html returns a small normalized payload
({"total": N, "jobs": [...]}) and the shared parse/total functions below read it.
"""

import json
import math
import re
from urllib.parse import urlsplit, urlunsplit

# US state and territory codes, for "City, ST" style locations.
US_STATE_CODES = frozenset(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM "
    "NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR".split()
)
_US_NAME_RE = re.compile(r"\b(united states|usa|u\.s\.a?\.?|us)\b", re.I)
US_STATE_NAMES = (
    "Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|"
    "Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|"
    "Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|"
    "New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|"
    "South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|"
    "Wisconsin|Wyoming|Washington, D\\.C\\.|District of Columbia"
)
_US_STATE_NAME_RE = re.compile(rf"\b({US_STATE_NAMES})\b")
_STATE_CODE_RE = re.compile(r",\s*([A-Z]{2})\b")
# "Toronto, ON, CA": CA is the country code for Canada here, not California.
_CANADA_RE = re.compile(r",\s*(AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT),\s*CA\s*$")


def is_us_location(location: str) -> bool:
    """True if any part of a location string ("A, CA; Remote - US; Austin, Texas") is in the US."""
    for part in re.split(r"[;|]", location or ""):
        if _CANADA_RE.search(part.strip()):
            continue
        if _US_NAME_RE.search(part):
            return True
        if any(code in US_STATE_CODES for code in _STATE_CODE_RE.findall(part)):
            return True
        # Full state names, e.g. "San Francisco, California" or "Remote - California".
        if _US_STATE_NAME_RE.search(part) and not re.search(r"\b(canada|australia|mexico)\b", part, re.I):
            return True
    return False


def build_search_url(search_url: str, page_num: int) -> str:
    return urlunsplit(urlsplit(search_url)._replace(fragment=f"page={page_num}"))


def page_num_from_url(url: str) -> int:
    fragment = urlsplit(url).fragment
    if fragment.startswith("page="):
        try:
            return max(1, int(fragment.split("=", 1)[1]))
        except ValueError:
            return 1
    return 1


def make_payload(jobs: list[dict], total: int | None) -> str:
    return json.dumps({"total": total, "jobs": jobs})


def parse_jobs(payload: str) -> list[dict]:
    try:
        return json.loads(payload).get("jobs") or []
    except (json.JSONDecodeError, AttributeError):
        return []


def get_total_results(payload: str) -> int | None:
    try:
        total = json.loads(payload).get("total")
    except (json.JSONDecodeError, AttributeError):
        return None
    return total if isinstance(total, int) and total > 0 else None


def total_pages_getter(page_size: int):
    def get_total_pages(payload: str) -> int | None:
        total = get_total_results(payload)
        return max(1, math.ceil(total / page_size)) if total else None

    return get_total_pages


def format_locations(locations: list[str]) -> str:
    locations = [loc.strip() for loc in locations if loc and loc.strip()]
    if not locations:
        return ""
    return f"{locations[0]}; +{len(locations) - 1} more" if len(locations) > 1 else locations[0]
