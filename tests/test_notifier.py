import asyncio

import notifier


def test_large_run_is_split_and_only_delivered_parts_are_marked(monkeypatch):
    calls = []

    async def fake_send(text, parse_mode=""):
        calls.append(text)
        return len(calls) != 2  # the second part fails

    monkeypatch.setattr(notifier, "_send_message", fake_send)
    jobs = [{"key": str(i), "title": f"Senior Software Engineer {i}", "url": f"https://x/{i}"} for i in range(200)]
    marked = []
    delivered = asyncio.run(
        notifier.send_run_summary([("Google", jobs)], on_delivered=lambda name, sent: marked.extend(sent))
    )

    assert len(calls) > 2
    assert all(len(text) <= 4096 for text in calls)
    assert "(1/" in calls[0].replace("\\", "")
    assert delivered == len(marked) < len(jobs)
