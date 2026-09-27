# FAANG+ Jobs Notifier

Got bored checking careers page for major tech companies so I vibe coded a Job Notifier (Scrapes every 10 mins).


A fully automated job-board monitor that scrapes career pages across 10 major tech and finance companies, deduplicates listings against a persisted state store, and fires real-time Telegram alerts the moment a new opening appears. Runs on GitHub Actions every 10 minutes so you never miss an application window.

## Features

- **10 companies out of the box** — Amazon, Apple, CVS Health (two adapters), Goldman Sachs, Google, Lyft, Meta, Salesforce, and Uber
- **Headless browser scraping** — Playwright + Chromium handles JS-heavy career pages and interactive pagination without brittle DOM hacks
- **Smart deduplication** — each company keeps its own `seen_jobs/<slug>.json` state file; jobs are tracked by stable ID so alerts never repeat
- **Real-time Telegram alerts** — richly-formatted notifications include title, team, location, post date, role ID, and a direct link to apply
- **Two scrape modes** — a fast *regular* scrape that alerts on new-since-last-run jobs, and a *full scrape* that seeds the seen-jobs state without sending alerts
- **Title filtering** — shared rules in `companies/filters.py` keep software-type IC roles from new grad through senior: titles must name an engineering role, and staff+/manager/director/intern/non-software engineering titles are dropped (whole-word matching)
- **Scraper health alerts** — a company that errors or returns 0 jobs for 3 runs in a row (`HEALTH_FAILURE_THRESHOLD`) triggers one Telegram "broken" alert, and one "recovered" alert when it works again; state lives in `seen_jobs/_health.json`
- **Plug-in adapter architecture** — adding a new company is a single file that implements `CompanyDefinition`; no core code changes required
- **GitHub Actions CI/CD** — both workflows commit updated state back to the repo, cache the Playwright browser binary, and handle concurrent run conflicts with `git pull --rebase`

## Supported Companies

| Slug | Company | Scrape Strategy |
|------|---------|----------------|
| `amazon` | Amazon | HTML parser |
| `apple` | Apple | HTML parser |
| `cvs` | CVS Health | HTML parser |
| `goldman-sachs` | Goldman Sachs | HTML parser |
| `google` | Google | `AF_initDataCallback` JSON payload |
| `lyft` | Lyft | CareerPuck public API |
| `meta` | Meta | GraphQL (`job_search_with_featured_jobs`) |
| `salesforce` | Salesforce | Workday adapter |
| `uber` | Uber | REST API (`loadSearchJobsResults`) |

## How It Works

```text
GitHub Actions (every 10 min)
  │
  └─► python scraper.py --company <slugs>
        │
        ├─ Launch headless Chromium via Playwright
        ├─ For each company adapter:
        │   ├─ Build paginated search URL(s)
        │   ├─ Fetch page HTML / API response
        │   ├─ Parse & normalise job records  ──► { title, team, location, posted, url, job_id }
        │   ├─ Deduplicate against seen_jobs/<slug>.json
        │   ├─ Apply title keyword / phrase filters
        │   └─ Send Telegram alert per new job  ──► 🔔 Telegram notification
        └─ Commit updated seen_jobs/ back to repo
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
3. Enable the **Multi-Company Jobs Notifier** workflow — it triggers on `workflow_dispatch` and can be wired to a cron schedule.

### Reliable 10-minute trigger (Cloudflare Worker)

GitHub's built-in cron often runs late or skips runs, so `dispatcher/` holds a
Cloudflare Worker whose cron trigger calls `workflow_dispatch` every 10 minutes.

1. Create a fine-grained GitHub token for this repository only, with
   **Actions: Read and write** permission.
2. From `dispatcher/`:

   ```bash
   npx wrangler@latest login
   npx wrangler@latest secret put GITHUB_TOKEN   # paste the token at the prompt
   npx wrangler@latest deploy
   ```

The `schedule:` trigger in `scrape.yml` stays as a backup; the workflow's
concurrency group prevents overlapping runs.

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
| `MAX_SEEN_JOBS` | No | `3000` | Cap on persisted job IDs per company |

## Adding a New Company

1. Create `companies/<slug>.py` and define a `CompanyDefinition` dataclass instance named `COMPANY`.
2. Implement `build_search_url`, `parse_jobs`, `get_total_pages`, and `get_total_results`.
3. Register it in `companies/registry.py`.
4. Add an empty `seen_jobs/<slug>.json` (`{}`).

That's it — the scraper, state manager, and notifier pick it up automatically.

## Project Structure

```
faang-jobs-notifier/
├── companies/          # One adapter file per company + shared base + registry
├── seen_jobs/          # Persisted job-ID state, one JSON file per company
├── scraper.py          # Entry point: incremental scrape + Telegram alerts
├── full_scrape.py      # Entry point: seed seen_jobs without sending alerts
├── runner.py           # Playwright page loading & pagination loop
├── state.py            # Deduplication, filtering, and state persistence
├── notifier.py         # Telegram message formatting and delivery
├── config.py           # Runtime configuration and env-var loading
└── .github/workflows/  # scrape.yml and full-scrape.yml
```

## Tech Stack

- **[Playwright](https://playwright.dev/python/)** — browser automation
- **[Beautiful Soup 4](https://www.crummy.com/software/BeautifulSoup/)** — HTML parsing
- **[httpx](https://www.python-httpx.org/)** — async HTTP for API-based adapters and Telegram
- **[python-dotenv](https://pypi.org/project/python-dotenv/)** — local env management
- **GitHub Actions** — scheduling and state commit-back
