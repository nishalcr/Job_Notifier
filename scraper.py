#!/usr/bin/env python3
"""
Multi-company jobs notifier.
Scrapes configured careers pages every run, queues newly seen jobs, and sends them
to Telegram as one daily digest (see digest.py).
"""

import argparse
import asyncio
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

import config
from details import add_job_details
from digest import queue_issue, queue_jobs, send_digest_if_due
from health import BROKEN, load_health, record_result, save_health
from notifier import verify_bot
from runner import LAST_ERRORS, collect_jobs
from state import (
    filter_new_jobs,
    is_seen_elsewhere,
    job_key,
    load_seen_jobs,
    mark_jobs_seen,
    passes_title_filters,
    posted_date,
    seed_seen_jobs,
)

# Companies scraped at the same time. Every run reads each company's full US job list
# (not just the newest pages), so no job is missed however a site orders its results.
CONCURRENCY = 8

# A company taking longer than this is stopped and counted as failed, so one stuck
# site cannot hold up the whole run (its jobs are picked up on the next run).
COMPANY_TIMEOUT_SECONDS = 360

# Jobs seen for the first time are alerted only if posted within this many days;
# older ones (open since before the bot tracked them) are marked seen quietly.
MAX_ALERT_AGE_DAYS = 30

# If a company's listing suddenly contains almost none of the jobs already saved for
# it (under FLOOD_KNOWN_SHARE) while many look new (FLOOD_MIN_JOBS or more), the site
# most likely changed its job IDs: everything is marked seen without alerts and a
# warning goes in the digest, instead of re-sending every job. (A listing where many jobs are new
# but most known ones are still there is a real catch-up and is alerted normally.)
FLOOD_KNOWN_SHARE = 0.1
FLOOD_MIN_JOBS = 50


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape configured company career sites and send alerts.")
    parser.add_argument(
        "--company",
        action="append",
        dest="companies",
        help="Company slug to scrape. Repeat or pass a comma-separated list.",
    )
    return parser.parse_args()


def _looks_like_id_change(new_jobs: list[dict], listed_jobs: list[dict]) -> bool:
    """True if many jobs look new while almost none of the saved ones are still listed."""
    known = len(listed_jobs) - len(new_jobs)
    return len(new_jobs) >= FLOOD_MIN_JOBS and known < FLOOD_KNOWN_SHARE * len(listed_jobs)


def _too_old(job: dict, today) -> bool:
    posted = posted_date(job.get("source_posted", ""), today)
    return posted is not None and (today - posted).days > MAX_ALERT_AGE_DAYS


async def _run_company_scrape(browser, slug: str, pending: list) -> tuple[bool, str]:
    """
    Scrape one company. Returns (ok, error message).

    Jobs to alert on are appended to pending as (runtime config, jobs); the run adds
    them to the daily digest queue at the end.
    """
    runtime_config = None

    try:
        runtime_config = config.get_company_runtime(slug)
        pages = max(runtime_config.max_pages, runtime_config.full_scrape_max_pages)
        unique_jobs = await collect_jobs(browser, runtime_config, pages)

        if not unique_jobs:
            if runtime_config.definition.allow_empty_results:
                print(
                    f"[scraper] WARNING: No jobs were extracted for "
                    f"{runtime_config.display_name}. Treating as non-fatal for this company."
                )
                return True, ""

            print(f"[scraper] No jobs were extracted for {runtime_config.display_name}.")
            return False, LAST_ERRORS.get(slug) or "No jobs extracted. The page structure may have changed."

        if not load_seen_jobs(runtime_config.slug):
            # First run for a company: record its current jobs without alerting.
            seed_seen_jobs(runtime_config, unique_jobs)
            print(f"[{runtime_config.slug}] First run: saved {len(unique_jobs)} current job(s) without alerts")
            return True, ""

        new_jobs = filter_new_jobs(runtime_config, unique_jobs)
        print(f"[{runtime_config.slug}] New jobs (not seen before): {len(new_jobs)}")
        if _looks_like_id_change(new_jobs, unique_jobs):
            mark_jobs_seen(runtime_config, new_jobs)
            message = (
                f"{len(new_jobs)} of {len(unique_jobs)} listed jobs looked new and almost none of the "
                "saved ones are still listed, so the site probably changed its job IDs. They were "
                "saved without alerts; check the adapter."
            )
            print(f"[{runtime_config.slug}] Flood guard: {message}")
            queue_issue(runtime_config.display_name, message)
            return True, ""

        to_alert = []
        skipped = []
        today = datetime.now(ZoneInfo(config.ALERT_TIMEZONE)).date()
        for job in new_jobs:
            if not passes_title_filters(job.get("title", ""), runtime_config):
                skipped.append(job)
            elif _too_old(job, today):
                skipped.append(job)
            elif is_seen_elsewhere(job, runtime_config.definition.shares_jobs_with):
                skipped.append(job)
            else:
                to_alert.append(job)
        if skipped:
            print(f"[{runtime_config.slug}] Skipped {len(skipped)} job(s) (title filter, posted over {MAX_ALERT_AGE_DAYS} days ago, or already alerted by a sibling adapter)")
        mark_jobs_seen(runtime_config, skipped)

        if to_alert:
            print(f"[{runtime_config.slug}] Found {len(to_alert)} new job(s) for the digest:")
            for job in to_alert:
                print(f"  - {job['title']}")
            pending.append((runtime_config, to_alert))
        else:
            print(f"[{runtime_config.slug}] No new jobs to notify.")

        print(
            f"[{runtime_config.slug}] Seen jobs database: "
            f"{len(load_seen_jobs(runtime_config.slug))} entries"
        )
        return True, ""
    except Exception as exc:
        print(f"[{slug}] Unexpected company failure: {exc}")
        return False, f"Unexpected error: {exc}"


def _queue_pending(pending: list) -> None:
    """Add the run's new jobs to the daily digest queue and mark them seen."""
    # Adapters for the same employer (CVS) run in parallel: queue a shared job once.
    queued: dict[str, set[str]] = {}
    total = 0
    for runtime_config, jobs in pending:
        siblings = runtime_config.definition.shares_jobs_with
        taken = set().union(*(queued.get(slug, set()) for slug in siblings))
        keep = [job for job in jobs if job_key(job) not in taken]
        queued[runtime_config.slug] = {job_key(job) for job in keep}
        # Queue first, then mark seen: a run that dies in between re-finds the job
        # next run, and queue_jobs ignores a job that is already queued.
        queue_jobs(runtime_config.display_name, runtime_config.slug, keep)
        mark_jobs_seen(runtime_config, jobs)
        total += len(keep)
    if total:
        print(f"[scraper] Added {total} job(s) to the daily digest queue")


async def _report_health(health: dict, slug: str, ok: bool, error: str) -> None:
    transition = record_result(health, slug, ok, error)
    if transition is None:
        return

    try:
        company_name = config.get_company_runtime(slug).display_name
    except Exception:
        company_name = slug

    if transition == BROKEN:
        failures = health[slug]["consecutive_failures"]
        print(f"[health] {company_name} marked broken after {failures} consecutive failures")
        queue_issue(company_name, f"Broken for {failures} consecutive runs. Last error: {error}")
    else:
        print(f"[health] {company_name} recovered")
        queue_issue(company_name, "Recovered ✅")


async def run_scraper(selected_companies: list[str] | None = None) -> None:
    """Main scraper entry point."""
    start_time = time.time()
    requested_companies = config.get_selected_company_slugs(selected_companies)

    print("=" * 60)
    print("[scraper] Multi-company jobs notifier starting")
    print(f"[scraper] Companies: {', '.join(requested_companies)}")
    print("=" * 60)

    bot_ok = await verify_bot()
    if not bot_ok:
        print("[scraper] WARNING: Telegram bot verification failed. Notifications may not work.")
        if not config.TELEGRAM_BOT_TOKEN:
            print("[scraper] TELEGRAM_BOT_TOKEN is not set.")
        if not config.TELEGRAM_CHAT_ID:
            print("[scraper] TELEGRAM_CHAT_ID is not set.")

    failed_companies = []
    health = load_health()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            results: dict[str, list] = {}
            semaphore = asyncio.Semaphore(CONCURRENCY)

            async def scrape(slug: str) -> None:
                async with semaphore:
                    company_pending: list = []
                    try:
                        ok, error = await asyncio.wait_for(
                            _run_company_scrape(browser, slug, company_pending), COMPANY_TIMEOUT_SECONDS
                        )
                    except asyncio.TimeoutError:
                        print(f"[{slug}] Stopped after {COMPANY_TIMEOUT_SECONDS}s")
                        ok, error = False, f"Timed out after {COMPANY_TIMEOUT_SECONDS // 60} minutes"
                        company_pending.clear()
                    results[slug] = company_pending
                    if not ok:
                        failed_companies.append(slug)
                    await _report_health(health, slug, ok, error)

            await asyncio.gather(*(scrape(slug) for slug in requested_companies))
            # Message order follows the company list, not finishing order.
            pending = [item for slug in requested_companies for item in results.get(slug, [])]
            try:
                await add_job_details(browser, [job for _, jobs in pending for job in jobs])
            except Exception as exc:
                print(f"[details] Skipped job details: {exc}")
            _queue_pending(pending)
        finally:
            await browser.close()
            save_health(health)

    try:
        await send_digest_if_due(requested_companies)
    except Exception as exc:
        print(f"[digest] Could not send the digest: {exc}")

    elapsed = time.time() - start_time
    print(f"\n[scraper] Run completed in {elapsed:.1f}s")

    if failed_companies:
        print(f"[scraper] Failed companies: {', '.join(failed_companies)}")
        sys.exit(1)


def main() -> None:
    args = parse_args()
    asyncio.run(run_scraper(args.companies))


if __name__ == "__main__":
    main()
