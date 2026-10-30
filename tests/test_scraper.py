"""End-to-end run behaviour with scraping and Telegram replaced by fakes."""

import asyncio
from datetime import date, timedelta

import pytest

import scraper
from state import load_seen_jobs


@pytest.fixture
def fake_run(seen_dir, monkeypatch):
    """Returns run(listings) -> {company name: [titles sent]} for one scraper run."""
    listings: dict[str, list[dict]] = {}
    sent: dict[str, list[str]] = {}

    async def fake_collect(browser, runtime_config, pages):
        return [dict(job) for job in listings.get(runtime_config.slug, [])]

    async def fake_send(groups, on_delivered=None):
        for name, jobs in groups:
            sent.setdefault(name, []).extend(job["title"] for job in jobs)
            if on_delivered:
                on_delivered(name, jobs)
        return sum(len(jobs) for _, jobs in groups)

    async def ok(*args, **kwargs):
        return True

    async def no_details(browser, jobs):
        return None

    class FakeBrowser:
        async def close(self):
            pass

    class FakePlaywright:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        @property
        def chromium(self):
            return self

        async def launch(self, **kwargs):
            return FakeBrowser()

    monkeypatch.setattr(scraper, "collect_jobs", fake_collect)
    monkeypatch.setattr(scraper, "send_run_summary", fake_send)
    monkeypatch.setattr(scraper, "add_job_details", no_details)
    monkeypatch.setattr(scraper, "async_playwright", FakePlaywright)
    for name in ("verify_bot", "send_error", "send_plain"):
        monkeypatch.setattr(scraper, name, ok)

    def run(new_listings: dict[str, list[dict]]) -> dict[str, list[str]]:
        listings.clear()
        listings.update(new_listings)
        sent.clear()
        asyncio.run(scraper.run_scraper(list(new_listings)))
        return dict(sent)

    return run


def job(key, title="Software Engineer", days_ago=0):
    posted = (date.today() - timedelta(days=days_ago)).isoformat()
    return {"key": key, "title": f"{title} {key}", "url": f"https://x/{key}", "posted": posted}


def test_first_run_seeds_then_only_new_jobs_are_sent_once(fake_run):
    assert fake_run({"pinterest": [job("1"), job("2")]}) == {}
    assert sorted(load_seen_jobs("pinterest")) == ["1", "2"]

    sent = fake_run({"pinterest": [job("1"), job("2"), job("3")]})
    assert sent == {"Pinterest": ["Software Engineer 3"]}

    assert fake_run({"pinterest": [job("1"), job("2"), job("3")]}) == {}


def test_new_job_anywhere_in_the_listing_is_found(fake_run):
    fake_run({"amazon": [job(str(i)) for i in range(100)]})
    listing = [job(str(i)) for i in range(100)]
    listing.insert(73, job("new"))
    assert fake_run({"amazon": listing}) == {"Amazon": ["Software Engineer new"]}


def test_same_title_openings_are_all_sent(fake_run):
    fake_run({"capitalone": [job("0")]})
    sent = fake_run({"capitalone": [job("0"), job("a", "Lead Data Engineer"), job("b", "Lead Data Engineer")]})
    assert len(sent["Capital One"]) == 2


def test_old_and_filtered_jobs_are_saved_without_alerts(fake_run):
    fake_run({"google": [job("0")]})
    sent = fake_run(
        {"google": [job("0"), job("old", days_ago=45), job("pm", "Product Manager"), job("ok", days_ago=3)]}
    )
    assert sent == {"Google": ["Software Engineer ok"]}
    assert {"old", "pm", "ok"} <= set(load_seen_jobs("google"))


def test_flood_guard_saves_without_alerts(fake_run):
    fake_run({"nvidia": [job(str(i)) for i in range(60)]})
    sent = fake_run({"nvidia": [job(f"new-id-{i}") for i in range(60)]})
    assert sent == {}
    assert len(load_seen_jobs("nvidia")) == 120


def test_job_listed_by_both_cvs_adapters_is_sent_once(fake_run):
    fake_run({"cvs": [job("0")], "cvs_wd": [job("0")]})
    sent = fake_run({"cvs": [job("0"), job("R1")], "cvs_wd": [job("0"), job("R1")]})
    assert sum(len(titles) for titles in sent.values()) == 1


def test_a_stuck_company_does_not_block_the_others(fake_run, monkeypatch):
    fake_run({"pinterest": [job("0")], "reddit": [job("0")]})
    real_collect = scraper.collect_jobs

    async def slow_for_pinterest(browser, runtime_config, pages):
        if runtime_config.slug == "pinterest":
            await asyncio.sleep(5)
        return await real_collect(browser, runtime_config, pages)

    monkeypatch.setattr(scraper, "collect_jobs", slow_for_pinterest)
    monkeypatch.setattr(scraper, "COMPANY_TIMEOUT_SECONDS", 0.2)
    with pytest.raises(SystemExit):  # a failed company makes the run exit non-zero
        fake_run({"pinterest": [job("0"), job("1")], "reddit": [job("0"), job("1")]})


def test_catch_up_with_many_new_jobs_is_not_mistaken_for_an_id_change(fake_run):
    fake_run({"apple": [job(str(i)) for i in range(40)]})
    listing = [job(str(i)) for i in range(40)] + [job(f"deep-{i}") for i in range(80)]
    sent = fake_run({"apple": listing})
    assert len(sent["Apple"]) == 80
