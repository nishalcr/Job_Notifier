"""Shared configuration for the multi-company jobs notifier."""

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from companies import get_company, list_companies
from companies.base import CompanyDefinition

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
# Timezone for the time shown in the per-run separator message.
ALERT_TIMEZONE = os.getenv("ALERT_TIMEZONE", "America/Phoenix")

# Scraping
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "15000"))
JOB_CARD_TIMEOUT = int(os.getenv("JOB_CARD_TIMEOUT", "8000"))

# State
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEEN_JOBS_DIR = os.path.join(BASE_DIR, "seen_jobs")
MAX_SEEN_JOBS = int(os.getenv("MAX_SEEN_JOBS", "3000"))

# Diagnostics
SCRAPE_ARTIFACTS_DIR = Path(
    os.getenv("SCRAPE_ARTIFACTS_DIR", os.path.join(BASE_DIR, "artifacts"))
)

DEFAULT_COMPANIES = ("apple",)


@dataclass(frozen=True)
class CompanyRuntimeConfig:
    definition: CompanyDefinition
    search_url: str
    max_pages: int
    full_scrape_max_pages: int

    @property
    def slug(self) -> str:
        return self.definition.slug

    @property
    def display_name(self) -> str:
        return self.definition.display_name

    @property
    def excluded_role_keywords(self) -> tuple[str, ...]:
        return self.definition.excluded_role_keywords

    @property
    def excluded_title_phrases(self) -> tuple[str, ...]:
        return self.definition.excluded_title_phrases


def _company_env_prefix(slug: str) -> str:
    return re.sub(r"[^A-Z0-9]", "_", slug.upper())


def _company_env_name(slug: str, setting: str) -> str:
    return f"{_company_env_prefix(slug)}_{setting}"


def _parse_company_list(raw_value: str) -> list[str]:
    items = [item.strip().lower() for item in raw_value.split(",") if item.strip()]
    unique_items = []
    seen_items = set()
    for item in items:
        if item not in seen_items:
            seen_items.add(item)
            unique_items.append(item)
    return unique_items


def get_selected_company_slugs(cli_companies: list[str] | None = None) -> list[str]:
    if cli_companies:
        requested = []
        for value in cli_companies:
            requested.extend(_parse_company_list(value))
    else:
        requested = _parse_company_list(os.getenv("COMPANIES", ",".join(DEFAULT_COMPANIES)))

    if not requested:
        requested = list(DEFAULT_COMPANIES)

    supported = set(list_companies())
    invalid = [slug for slug in requested if slug not in supported]
    if invalid:
        supported_list = ", ".join(sorted(supported))
        invalid_list = ", ".join(invalid)
        raise ValueError(f"Unsupported companies: {invalid_list}. Supported companies: {supported_list}")

    return requested


def get_company_runtime(slug: str) -> CompanyRuntimeConfig:
    definition = get_company(slug)
    search_url = os.getenv(
        _company_env_name(definition.slug, "SEARCH_URL"),
        definition.default_search_url,
    )
    max_pages = int(
        os.getenv(
            _company_env_name(definition.slug, "MAX_PAGES"),
            str(definition.default_max_pages),
        )
    )
    full_scrape_max_pages = int(
        os.getenv(
            _company_env_name(definition.slug, "FULL_SCRAPE_MAX_PAGES"),
            str(definition.default_full_scrape_max_pages),
        )
    )
    return CompanyRuntimeConfig(
        definition=definition,
        search_url=search_url,
        max_pages=max_pages,
        full_scrape_max_pages=full_scrape_max_pages,
    )
