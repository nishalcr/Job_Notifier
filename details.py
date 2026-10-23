"""
Read extra details (pay range, years of experience, work arrangement) from job pages.

Only the jobs a run is about to alert on are opened, each once, with a short timeout.
Anything that cannot be read is left out of the message; it never blocks an alert.
"""

import asyncio
import re
import time

# Stop opening pages after this long, so a slow site cannot delay a run's message.
TIME_BUDGET_SECONDS = 150
PAGE_TIMEOUT_MS = 20000
MAX_JOBS_PER_RUN = 40

_AMOUNT = r"(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d+)?\s?[kK])(?:\.\d{2})?"
_SALARY_RE = re.compile(rf"\$\s?{_AMOUNT}\s*(?:USD\s*)?(?:-|–|—|to)\s*(?:USD\s*)?\$?\s?{_AMOUNT}")
_YEARS_RE = re.compile(
    r"(?<![\d.])(\d{1,2})\s*(?:\+|or more|or greater)?\s*(?:(?:-|–|to)\s*(\d{1,2})\s*\+?)?\s*\+?\s*years?",
    re.I,
)


def _amount_to_dollars(text: str) -> float:
    text = text.replace(",", "").replace(" ", "").lower()
    return float(text[:-1]) * 1000 if text.endswith("k") else float(text)


def extract_salary(text: str) -> str:
    """Annual US pay range, e.g. "$150K–$210K" (widest range when several are listed)."""
    lows, highs = [], []
    for low, high in _SALARY_RE.findall(text):
        low_dollars, high_dollars = _amount_to_dollars(low), _amount_to_dollars(high)
        # Skip hourly rates and anything that is not a plausible yearly salary range.
        if 20000 <= low_dollars <= high_dollars <= 2000000:
            lows.append(low_dollars)
            highs.append(high_dollars)
    if not lows:
        return ""
    return f"${round(min(lows) / 1000)}K–${round(max(highs) / 1000)}K"


def extract_years(text: str) -> str:
    """Minimum years of experience asked for, e.g. "5+ yrs" or "3–5 yrs"."""
    for match in _YEARS_RE.finditer(text):
        after = text[match.end(): match.end() + 80].lower()
        if "experience" not in after and "industry" not in after:
            continue
        low, high = int(match.group(1)), match.group(2)
        if not 0 < low <= 20:
            continue
        if high and low < int(high) <= 25:
            return f"{low}–{int(high)} yrs"
        return f"{low}+ yrs"
    return ""


def extract_work_type(text: str, location: str = "", title: str = "") -> str:
    """Remote, Hybrid or Onsite when the posting says so."""
    if re.search(r"\bremote\b", f"{location} {title}", re.I):
        return "Remote"
    lowered = text.lower()
    if re.search(r"\bhybrid\b", lowered):
        return "Hybrid"
    if re.search(r"\b(fully remote|remote[- ]first|remote eligible|remote position|this role is remote|work from home)\b", lowered):
        return "Remote"
    if re.search(r"\b(on-?site|in-office|in office)\b", lowered):
        return "Onsite"
    return ""


async def _page_text(context, url: str) -> str:
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        return await page.inner_text("body", timeout=5000)
    finally:
        await page.close()


async def add_job_details(browser, jobs: list[dict]) -> None:
    """Fill salary, years and work_type on each job (in place) from its page."""
    deadline = time.monotonic() + TIME_BUDGET_SECONDS
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    )
    try:
        for job in jobs[:MAX_JOBS_PER_RUN]:
            if time.monotonic() > deadline:
                print("[details] Time budget used up; remaining jobs are sent without details")
                break
            url = job.get("url")
            if not url:
                continue
            try:
                text = await asyncio.wait_for(_page_text(context, url), PAGE_TIMEOUT_MS / 1000 + 15)
            except Exception as exc:
                print(f"[details] Could not read {url}: {exc.__class__.__name__}")
                continue
            job["salary"] = extract_salary(text)
            job["years"] = extract_years(text)
            job["work_type"] = extract_work_type(text, job.get("location", ""), job.get("title", ""))
    finally:
        await context.close()
