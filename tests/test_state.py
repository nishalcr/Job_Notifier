from datetime import date

import config
from state import filter_new_jobs, load_seen_jobs, mark_jobs_seen, posted_date, seed_seen_jobs

TODAY = date(2026, 10, 30)


def test_posted_date_formats():
    assert posted_date("2026-10-29", TODAY) == date(2026, 10, 29)
    assert posted_date("2026-10-29T18:59:06Z", TODAY) == date(2026, 10, 29)
    assert posted_date("October 29, 2026", TODAY) == date(2026, 10, 29)
    assert posted_date("Oct 8, 2026", TODAY) == date(2026, 10, 8)
    assert posted_date("Posted Today", TODAY) == TODAY
    assert posted_date("Posted Yesterday", TODAY) == date(2026, 10, 29)
    assert posted_date("Posted 3 Days Ago", TODAY) == date(2026, 10, 27)
    assert posted_date("Posted 30+ Days Ago", TODAY) == date(2026, 9, 30)
    assert posted_date("", TODAY) is None
    assert posted_date("Multiple Locations", TODAY) is None


def _jobs(*keys):
    return [{"key": key, "title": f"Software Engineer {key}", "url": "u"} for key in keys]


def test_new_jobs_are_found_until_marked_seen(seen_dir):
    runtime_config = config.get_company_runtime("pinterest")
    assert [job["key"] for job in filter_new_jobs(runtime_config, _jobs("1", "2"))] == ["1", "2"]
    # Not saved until delivered: a failed send is retried next run.
    assert len(filter_new_jobs(runtime_config, _jobs("1", "2"))) == 2
    mark_jobs_seen(runtime_config, _jobs("1"))
    assert [job["key"] for job in filter_new_jobs(runtime_config, _jobs("1", "2"))] == ["2"]


def test_seeding_merges_and_never_removes(seen_dir):
    runtime_config = config.get_company_runtime("pinterest")
    seed_seen_jobs(runtime_config, _jobs("1", "2"))
    seed_seen_jobs(runtime_config, [])
    seed_seen_jobs(runtime_config, _jobs("3"))
    assert sorted(load_seen_jobs("pinterest")) == ["1", "2", "3"]


def test_request_with_retry_retries_server_errors(monkeypatch):
    import asyncio

    from companies import json_api

    async def no_sleep(seconds):
        return None

    monkeypatch.setattr(json_api.asyncio, "sleep", no_sleep)
    statuses = iter([502, 503, 200])

    class Response:
        def __init__(self, status):
            self.status = status

    async def send():
        return Response(next(statuses))

    assert asyncio.run(json_api.request_with_retry(send)).status == 200
