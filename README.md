# FAANG+ Jobs Notifier

Got bored checking careers page for major tech companies so I vibe coded a Job Notifier (Scrapes every 10 mins).


A fully automated job-board monitor that scrapes career pages across 40 tech and finance companies, deduplicates listings against a persisted state store, and sends one Telegram message per run with every new opening. Runs on GitHub Actions every 10 minutes so you never miss an application window.

> **Operations guide:** current status, every company's configuration, filters, triggers and runbooks are in [docs/OPERATIONS.md](docs/OPERATIONS.md).

## Features

- **44 companies out of the box** — Adobe, Amazon, AMD, Atlassian, American Express, Apple, Capital One, Cerebras, Cisco, CVS Health (two adapters), Databricks, Dell, Disney, DoorDash, Ford, GoDaddy, Goldman Sachs, Google, HP, IBM, Intel, Intuit, JPMorgan Chase, Lyft, Meta, Microsoft, Netflix, NVIDIA, Oracle, Palo Alto Networks, Paramount, PayPal, Pinterest, Red Hat, Reddit, Salesforce, Samsung, Snowflake, Spotify, Stripe, Uber, Yahoo, and Zscaler
- **Headless browser scraping** — Playwright + Chromium handles JS-heavy career pages and interactive pagination without brittle DOM hacks
- **Full-list comparison** — every run reads each company's complete US listing (in parallel) and compares it with `seen_jobs/<slug>.json`, so a new job is found wherever the site puts it; jobs are marked seen as soon as their message is delivered, so alerts never repeat
- **One Telegram message per run** — every new job a run finds arrives in a single message, grouped by company, with the title linked to the posting plus location, post date, pay range, years of experience, remote/hybrid/onsite, team and job ID when the posting lists them (`details.py`; long runs are split into numbered parts)
- **Two scrape modes** — a fast *regular* scrape that alerts on new-since-last-run jobs, and a *full scrape* that seeds the seen-jobs state without sending alerts
- **Title filtering** — shared rules in `companies/filters.py`: US-only SWE, data, ML and AI roles at every level; managers, directors, VPs, interns, customer-facing and hardware engineering roles are dropped (whole-word matching)
- **Scraper health alerts** — a company that errors or returns 0 jobs for 3 runs in a row (`HEALTH_FAILURE_THRESHOLD`) triggers one Telegram "broken" alert, and one "recovered" alert when it works again; state lives in `seen_jobs/_health.json`
- **Plug-in adapter architecture** — adding a new company is a single file that implements `CompanyDefinition`; no core code changes required
- **GitHub Actions CI/CD** — both workflows commit updated state back to the repo, cache the Playwright browser binary, and handle concurrent run conflicts with `git pull --rebase`

## Supported Companies

| Source | Companies |
|--------|-----------|
| Workday jobs API (`companies/workday.py`) | Adobe, Capital One, Cisco, CVS (Workday), Disney, HP, Intel, NVIDIA, Palo Alto Networks, PayPal, Red Hat, Salesforce, Samsung, Yahoo |
| Greenhouse boards API (`companies/greenhouse.py`) | Databricks, DoorDash, GoDaddy, Pinterest, Reddit, Stripe, Zscaler |
| Oracle Recruiting Cloud API (`companies/oracle_hcm.py`) | American Express, Dell, Ford, JPMorgan Chase, Oracle |
| Ashby / Lever / Eightfold | Cerebras, Snowflake / Spotify / Netflix |
| Company-specific | Amazon (`search.json`), AMD (Jibe API), Atlassian (listings JSON), Intuit (Radancy results), Apple (embedded JSON), CVS (HTML), Goldman Sachs, Google (`AF_initDataCallback`), IBM (search API), Lyft (CareerPuck API), Meta (GraphQL), Microsoft (Eightfold PCSX), Paramount (SuccessFactors HTML), Uber (in-page API fetch) |

Per-company pages, site-side filters and notes are in [docs/OPERATIONS.md](docs/OPERATIONS.md#companies-44).

## How It Works

```text
cron-job.org → workflow_dispatch (every 10 min)
  │
  └─► python scraper.py --company <slugs>
        │
        ├─ Launch headless Chromium via Playwright
        ├─ For each company adapter:
        │   ├─ Build paginated search URL(s)
        │   ├─ Fetch page HTML / API response
        │   ├─ Parse & normalise job records  ──► { title, team, location, posted, url, job_id }
        │   ├─ Deduplicate against seen_jobs/<slug>.json
        │   └─ Apply title / US filters, queue new jobs
        ├─ Open each new job's page for pay, experience, work type (details.py)
        ├─ Send one Telegram message for the run  ──► 🔔 Telegram notification
        └─ Commit updated seen_jobs/ back to repo (push retried)
```

## Setup

### Prerequisites

- Python 3.12+
- A [Telegram bot token and chat ID](https://core.telegram.org/bots#how-do-i-create-a-bot)

### Local

```bash
git clone https://github.com/<you>/faang-jobs-notifier.git
cd faang-jobs-notifier

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

cp .env.example .env   # fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
```

### GitHub Actions

1. Fork / push to your own repository.
2. Add two repository secrets: `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
3. Seed the seen-jobs state once with the **Full Scrape** workflow (no alerts).
4. Point an external scheduler (this fork uses cron-job.org) at the `scrape.yml` `workflow_dispatch` endpoint every 10 minutes. GitHub's own `schedule:` trigger fired too rarely to rely on. See [docs/OPERATIONS.md](docs/OPERATIONS.md#external-trigger-cron-joborg).

## Usage

```bash
# Scrape all companies (uses DEFAULT_COMPANIES from config)
python scraper.py

# Scrape specific companies
python scraper.py --company apple --company google
python scraper.py --company apple,google,meta   # comma-separated also works

# Seed seen_jobs/ without sending alerts (run once before enabling notifications)
python full_scrape.py
python full_scrape.py --company amazon,uber
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Yes | — | Target chat / channel ID |
| `PAGE_LOAD_TIMEOUT` | No | `15000` | Playwright page load timeout (ms) |
| `JOB_CARD_TIMEOUT` | No | `8000` | Selector wait timeout (ms) |
| `MAX_SEEN_JOBS` | No | `50000` | Cap on persisted job IDs per company |
| `COMPANIES` | No | `apple` | Comma-separated slugs (the workflows pass all 44) |
| `ALERT_TIMEZONE` | No | `America/Phoenix` | Time zone of the message header |
| `HEALTH_FAILURE_THRESHOLD` | No | `3` | Consecutive failures before a "broken" alert |

## Adding a New Company

1. Create `companies/<slug>.py` defining `COMPANY`, usually with a shared builder (`workday_company`, `greenhouse_company`, `oracle_hcm_company`, `ashby_company`, `lever_company`, `eightfold_company`).
2. Register it in `companies/registry.py`.
3. Seed it without alerts: `python full_scrape.py --company <slug>` and commit `seen_jobs/` (`git add -f`).
4. Add the slug to the company lists in `scrape.yml` and `full-scrape.yml`.

Full checklist: [docs/OPERATIONS.md](docs/OPERATIONS.md#add-a-company).

## Project Structure

```
faang-jobs-notifier/
├── companies/          # One adapter file per company + shared base + registry
├── seen_jobs/          # Persisted job-ID state, one JSON file per company
├── docs/OPERATIONS.md  # Status, configuration and runbooks
├── scraper.py          # Entry point: incremental scrape + Telegram alerts
├── full_scrape.py      # Entry point: seed seen_jobs without sending alerts
├── send_recent.py      # Entry point: re-send jobs posted on a given day
├── details.py          # Pay range / experience / work type from job pages
├── health.py           # Broken / recovered tracking
├── runner.py           # Playwright page loading & pagination loop
├── state.py            # Deduplication, filtering, and state persistence
├── notifier.py         # Telegram message formatting and delivery
├── config.py           # Runtime configuration and env-var loading
└── .github/workflows/  # scrape.yml, full-scrape.yml, send-recent.yml
```

## Tech Stack

- **[Playwright](https://playwright.dev/python/)** — browser automation
- **[Beautiful Soup 4](https://www.crummy.com/software/BeautifulSoup/)** — HTML parsing
- **[httpx](https://www.python-httpx.org/)** — async HTTP for API-based adapters and Telegram
- **[python-dotenv](https://pypi.org/project/python-dotenv/)** — local env management
- **GitHub Actions** — scheduling and state commit-back
