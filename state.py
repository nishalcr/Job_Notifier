"""State management for seen jobs across multiple company-specific files."""

import json
import os
import re
import time
from datetime import date
from typing import Any, Sequence

import config
from companies.filters import HARDWARE_DOMAIN_PHRASES, SOFTWARE_TITLE_KEYWORDS, TARGET_LEVEL_KEYWORDS
from config import CompanyRuntimeConfig

STATE_VERSION = 3

# Rewrites applied before matching. "Senior Staff" is still staff level, and
# Salesforce spells out its levels as "... Member of Technical Staff".
_TITLE_NORMALIZATIONS = (
    ("senior staff", "staff"),
    ("sr. staff", "staff"),
    ("sr staff", "staff"),
    ("senior principal", "principal"),
    ("sr. principal", "principal"),
    ("sr principal", "principal"),
    # "Senior Lead" sits above "Lead" (e.g. JPMorgan Executive Director level).
    ("senior lead", "principal"),
    ("sr. lead", "principal"),
    ("sr lead", "principal"),
    ("associate member of technical staff", "amts"),
    ("senior member of technical staff", "smts"),
    ("lead member of technical staff", "lmts"),
    ("principal member of technical staff", "pmts"),
    ("member of technical staff", "mts"),
)


def _company_state_file(company_slug: str) -> str:
    return os.path.join(config.SEEN_JOBS_DIR, f"{company_slug}.json")


def _ensure_state_dir() -> None:
    os.makedirs(config.SEEN_JOBS_DIR, exist_ok=True)


def _empty_company_state(company_slug: str) -> dict[str, Any]:
    return {
        "_meta": {"version": STATE_VERSION, "company": company_slug},
        "jobs": {},
    }


def _normalize_company_state(company_slug: str, data: Any) -> dict[str, Any]:
    state = _empty_company_state(company_slug)
    if not isinstance(data, dict):
        return state

    if isinstance(data.get("jobs"), dict):
        state["jobs"] = data["jobs"]
        return state

    state["jobs"] = data
    return state


def _load_company_state(company_slug: str) -> dict[str, Any]:
    state_file = _company_state_file(company_slug)
    if not os.path.exists(state_file):
        return _empty_company_state(company_slug)

    try:
        with open(state_file, "r") as handle:
            return _normalize_company_state(company_slug, json.load(handle))
    except (json.JSONDecodeError, IOError):
        return _empty_company_state(company_slug)


def _prune_seen_jobs(seen: dict[str, Any]) -> dict[str, Any]:
    if len(seen) <= config.MAX_SEEN_JOBS:
        return seen

    sorted_keys = sorted(seen, key=lambda key: seen[key].get("first_seen", 0))
    excess = len(seen) - config.MAX_SEEN_JOBS
    for key in sorted_keys[:excess]:
        del seen[key]
    return seen


def load_seen_jobs(company_slug: str) -> dict[str, Any]:
    return _load_company_state(company_slug)["jobs"]


def save_seen_jobs(company_slug: str, seen: dict[str, Any]) -> None:
    _ensure_state_dir()
    state = _empty_company_state(company_slug)
    state["jobs"] = _prune_seen_jobs(dict(seen))
    with open(_company_state_file(company_slug), "w") as handle:
        json.dump(state, handle, indent=2)


def _contains_term(text: str, term: str) -> bool:
    """Whole-word, case-insensitive match (so "sr" does not match "SRE")."""
    term = term.strip().lower()
    if not term:
        return False
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text.lower()) is not None


def _normalize_title(title: str) -> str:
    text = " ".join(title.lower().split())
    for phrase, replacement in _TITLE_NORMALIZATIONS:
        text = text.replace(phrase, replacement)
    return text


def is_excluded_role(title: str, excluded_role_keywords: Sequence[str]) -> bool:
    """
    Return True if the title names a level above the target range.

    Multi-level postings such as "Senior / Lead / Principal Software Engineer"
    are kept when they also name a target level (new grad through senior).
    """
    text = _normalize_title(title)
    if not any(_contains_term(text, keyword) for keyword in excluded_role_keywords):
        return False
    return not any(_contains_term(text, keyword) for keyword in TARGET_LEVEL_KEYWORDS)


def passes_title_filters(title: str, runtime_config: CompanyRuntimeConfig) -> bool:
    """Return True if a job title should be kept (and alerted on)."""
    text = _normalize_title(title)
    if not text:
        return False

    included = runtime_config.definition.included_title_keywords
    if included and not any(_contains_term(text, keyword) for keyword in included):
        return False

    is_software = any(_contains_term(text, keyword) for keyword in SOFTWARE_TITLE_KEYWORDS)
    for phrase in runtime_config.excluded_title_phrases:
        if not _contains_term(text, phrase):
            continue
        if is_software and phrase in HARDWARE_DOMAIN_PHRASES:
            continue
        return False

    return not is_excluded_role(text, runtime_config.excluded_role_keywords)


def _today_date_string() -> str:
    return date.today().isoformat()


def _job_state_payload(job: dict, posted_override: str | None = None) -> dict[str, Any]:
    return {
        "first_seen": time.time(),
        "posted": posted_override if posted_override is not None else job.get("posted", ""),
        "title": job.get("title", ""),
        "job_id": job.get("job_id") or job.get("role_number") or job.get("key", ""),
        "url": job.get("url", ""),
    }


def _resolve_posted_value(job: dict, strategy: str, today: str) -> str:
    if strategy in {"empty", "blank"}:
        return ""
    if strategy in {"today", "new-only-today", "all-found-today"}:
        return today
    return job.get("posted", "")


def _job_key(job: dict) -> str:
    return job.get("key") or job.get("job_id") or job.get("role_number") or ""


def filter_new_jobs(runtime_config: CompanyRuntimeConfig, jobs: list[dict]) -> list[dict]:
    """
    Return jobs that are not in the seen store yet.

    New jobs are not saved here: call mark_jobs_seen once each one has been
    alerted or deliberately skipped, so a failed Telegram send is retried on
    the next run instead of being lost.
    """
    seen = load_seen_jobs(runtime_config.slug)
    new_jobs = []
    discovered_on = _today_date_string()
    strategy = runtime_config.definition.regular_scrape_posted_strategy
    changed = False

    for job in jobs:
        key = _job_key(job)
        if not key:
            continue
        job.setdefault("source_posted", job.get("posted", ""))
        posted_value = _resolve_posted_value(job, strategy, discovered_on)
        job["posted"] = posted_value

        if key not in seen:
            new_jobs.append(job)
            continue

        if strategy == "all-found-today":
            first_seen = seen[key].get("first_seen", time.time())
            seen[key] = _job_state_payload(job, posted_override=posted_value)
            seen[key]["first_seen"] = first_seen
            changed = True

    if changed:
        save_seen_jobs(runtime_config.slug, seen)

    return new_jobs


def mark_jobs_seen(runtime_config: CompanyRuntimeConfig, jobs: list[dict]) -> None:
    if not jobs:
        return
    seen = load_seen_jobs(runtime_config.slug)
    for job in jobs:
        key = _job_key(job)
        if key and key not in seen:
            seen[key] = _job_state_payload(job, posted_override=job.get("posted", ""))
    save_seen_jobs(runtime_config.slug, seen)


def is_seen_elsewhere(job: dict, company_slugs: Sequence[str]) -> bool:
    """True if another adapter for the same employer already saw this job ID."""
    key = _job_key(job)
    return bool(key) and any(key in load_seen_jobs(slug) for slug in company_slugs)


def replace_seen_jobs(runtime_config: CompanyRuntimeConfig, jobs: list[dict]) -> None:
    seen = {}
    posted_strategy = runtime_config.definition.full_scrape_posted_strategy
    today = _today_date_string()

    for job in jobs:
        key = _job_key(job)
        if not key:
            continue
        seen[key] = _job_state_payload(
            job,
            posted_override=_resolve_posted_value(job, posted_strategy, today),
        )
    save_seen_jobs(runtime_config.slug, seen)
