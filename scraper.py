#!/usr/bin/env python3
"""
Multi-company jobs notifier.
Scrapes configured careers pages and sends Telegram alerts for newly seen jobs.
"""

import argparse
import asyncio
import sys
import time

from playwright.async_api import async_playwright

import config
from health import BROKEN, load_health, record_result, save_health
from notifier import send_error, send_job_alert_for_company, send_plain, send_summary, verify_bot
from runner import LAST_ERRORS, collect_jobs
from state import filter_new_jobs, load_seen_jobs, passes_title_filters


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape configured company career sites and send alerts.")
    parser.add_argument(
        "--company",
        action="append",
        dest="companies",
        help="Company slug to scrape. Repeat or pass a comma-separated list.",
    )
    return parser.parse_args()


async def _run_company_scrape(browser, slug: str) -> tuple[bool, str]:
    """Scrape one company. Returns (ok, error message)."""
    runtime_config = None

    try:
        runtime_config = config.get_company_runtime(slug)
        unique_jobs = await collect_jobs(browser, runtime_config, runtime_config.max_pages)

        if not unique_jobs:
            if runtime_config.definition.allow_empty_results:
                print(
                    f"[scraper] WARNING: No jobs were extracted for "
                    f"{runtime_config.display_name}. Treating as non-fatal for this company."
                )
                return True, ""

            print(f"[scraper] No jobs were extracted for {runtime_config.display_name}.")
            return False, LAST_ERRORS.get(slug) or "No jobs extracted. The page structure may have changed."

        new_jobs = filter_new_jobs(runtime_config, unique_jobs)
        print(f"[{runtime_config.slug}] New jobs (not seen before): {len(new_jobs)}")

        before = len(new_jobs)
        new_jobs = [job for job in new_jobs if passes_title_filters(job.get("title", ""), runtime_config)]
        excluded = before - len(new_jobs)
        if excluded:
            print(f"[{runtime_config.slug}] Excluded {excluded} job(s) by title filter")

        if new_jobs:
            print(f"[{runtime_config.slug}] Sending {len(new_jobs)} Telegram notification(s)...")
            for index, job in enumerate(new_jobs, 1):
                print(f"  [{index}/{len(new_jobs)}] {job['title']}")
                success = await send_job_alert_for_company(runtime_config.display_name, job)
                if not success:
                    print(f"[{runtime_config.slug}] Failed to send notification")
                if index < len(new_jobs):
                    await asyncio.sleep(0.5)
            await send_summary(runtime_config.display_name, len(new_jobs), len(unique_jobs))
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
        await send_error(company_name, f"Broken for {failures} consecutive runs. Last error: {error}")
    else:
        print(f"[health] {company_name} recovered")
        await send_plain(f"✅ {company_name} scraper recovered.")


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
            for slug in requested_companies:
                ok, error = await _run_company_scrape(browser, slug)
                if not ok:
                    failed_companies.append(slug)
                await _report_health(health, slug, ok, error)
        finally:
            await browser.close()
            save_health(health)

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
