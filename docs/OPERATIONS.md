# Job Notifier: Status, Configuration and Runbook

Last updated: 2026-10-30. Repo: `nishalcr/Job_Notifier` (fork of `rohitdanti/FAANG-Job-Notifier`).

> The clone has two remotes (`origin` = the fork, `upstream` = rohitdanti). Always pass
> `-R nishalcr/Job_Notifier` to `gh`, or it acts on upstream.

## Current status

- **Live.** 44 companies are scraped every 10 minutes on GitHub Actions; new jobs arrive in Telegram.
- **Live and verified (2026-10-30).** 44 companies; every run reads each company's **full** US job list
  (about 26,600 jobs) and alerts every matching job not seen before.
  - First run on this design (19:20 UTC) sent a one-time catch-up of 350 missed jobs from the last 30 days, in 295 s.
  - First normal run after it (19:30 UTC) sent 5 new jobs in 230 s.
  - Runs take 4–5 minutes. Opening job pages for details adds up to 2.5 minutes when there are many new jobs.
  - No company is marked broken (`seen_jobs/_health.json` is `{}`).
- Tests: `.venv/bin/python -m pytest -q` (also run by `.github/workflows/tests.yml` on every code push).

## How a run works

1. **Trigger.** A cron-job.org job (the user's account) POSTs a `workflow_dispatch` to
   `.github/workflows/scrape.yml` every 10 minutes, using a fine-grained GitHub token.
   GitHub's own `schedule:` trigger is not used: it fired too rarely.
2. **Scrape.** `scraper.py` reads every company's **complete** current US listing, 8 companies at a time
   (`CONCURRENCY`). Sites that serve listings as data (Workday, Oracle, Eightfold, Microsoft, Amazon, Apple,
   AMD, IBM, Intuit) fetch 4 pages at a time (`page_concurrency`). Brief server errors (429/5xx) are retried.
   A company taking over 6 minutes is stopped and counted as failed (`COMPANY_TIMEOUT_SECONDS`), so one stuck
   site cannot hold up the run.
   Reading the full list, not just the newest pages, is what guarantees no job is missed: some sites do not
   sort by post date (Amazon), and Workday jobs can go live with an earlier post date, landing deep in the list.
3. **Decide what is new.** The current listing is compared with `seen_jobs/<slug>.json`; any job not in it is new. A new job is alerted if:
   - it passes the title filters and is in the US;
   - another adapter for the same employer has not already sent it (CVS has two);
   - its post date, when known, is within 30 days (`MAX_ALERT_AGE_DAYS`), so jobs open since before the bot tracked them are not alerted.
   Every opening is alerted, including several openings with the same title.
   Jobs that fail a check are marked seen silently. Special cases:
   - **First run for a company** (no saved state): its current jobs are saved without alerts.
   - **Flood guard:** if 50+ jobs look new while under 10% of the saved jobs are still listed, the site most
     likely changed its job IDs. Everything is saved without alerts and one warning is sent.
4. **Details.** Each job about to be alerted has its page opened once (`details.py`) to read
   the pay range, years of experience and Remote/Hybrid/Onsite. The cap is 40 jobs and 150 s per run.
5. **Send.** One Telegram message per run, grouped by company. It is split into numbered parts if it is over 3800 characters.
6. **Save.** Each job is marked seen as soon as the part containing it is delivered. The
   workflow then commits `seen_jobs/` (push retried up to 5 times).

### Message format

```
🔔 3 new jobs · Oct 23, 12:40 PM

Snowflake · 1
• Software Engineer                      (title links to the posting)
    📍 Bellevue, WA  🗓 Oct 22
    💰 $160K–$230K  🧑‍💻 4+ yrs  🏠 Hybrid
    🏢 Engineering  🆔 R1004306
```

Missing details are left out. Pay is found on roughly two thirds of postings. Amazon, Google, Meta,
Apple, NVIDIA, JPMC, Dell, IBM and AMD often show no readable range. Work type is a best guess
from the page text.

Other messages:
- `⚠️ <Company> Jobs Scraper Error`: a company failed 3 runs in a row (`HEALTH_FAILURE_THRESHOLD`).
- `✅ <Company> scraper recovered.`: sent when it works again.
- Health state lives in `seen_jobs/_health.json`.

## Never sending the same alert twice

| Risk | Protection |
|---|---|
| Run dies after sending | Jobs marked seen per delivered message part, not at the end |
| State push fails (GitHub 500) | Push retried 5× with backoff; error annotation if all fail |
| Job times out before saving | Scraper step timeout (14 min) < job timeout (18 min), so the save step always runs |
| Telegram reply lost after posting | Read timeout counts as sent; only connect errors are retried |
| Queued run uses stale state | Checkout uses `ref: ${{ github.ref_name }}` (branch tip); concurrency group `seen-jobs-state` |
| Seeding during an outage wipes state | `full_scrape.py` merges into the store and skips companies that return 0 jobs |
| Old entries pruned then re-seen | `MAX_SEEN_JOBS` = 50000 per company |
| Site changes its job IDs | Flood guard: saved without alerts, one warning |
| Same job on both CVS feeds in one run | Queued jobs of sibling adapters are checked too |

In the week before these fixes, 1 duplicate was found in 958 alerts; it was caused by a failed push.

## Filters (`companies/filters.py`)

Target: about 5 years of experience, **US only**, **SWE, data, ML and AI roles at every level**, individual contributors.

- **Title must contain** (whole word, plurals count) a word from `ENGINEERING_TITLE_KEYWORDS`:
  - engineer, developer, programmer, software, SDE, SDET, SWE, SRE, DevOps, full stack/FullStack, MLE;
  - machine learning, ML, deep learning, scientist, researcher, data analyst, business/product analyst, analytics, BI, quantitative;
  - architect, technical staff, Salesforce MTS levels.
  - Common typos ("Enginner") and joined levels ("SWE2") are normalized first.
- **Dropped:**
  - Managers, directors ("Dir,"), supervisors, TPMs, "head of", leaders, interns and co-ops. Cisco's "Technical Leader" is an individual-contributor title and is kept.
  - VP and vice president, except at Goldman, where VP is an individual-contributor level.
  - Customer-facing roles: sales, pre-sales, solutions, customer, field, support, partner, consulting and technical-marketing engineers; solutions architects, consultants, developer advocates, account executives.
  - Specialists, recruiters, contractors, administrative and business-partner roles.
  - UX, user, design and market researchers.
  - Hardware, chip, fab, data-center, automotive and audio/visual engineering. These are kept if the title also says software, firmware, ML, SRE, DevOps, data engineer or full stack.
- **Core-role override:** a title naming a core role (`CORE_ROLE_PHRASES`: software engineer, SDE, data engineer/scientist, ML engineer/scientist, research/applied scientist, full stack, SRE, platform engineer, BI engineer) is kept despite any non-software or hardware phrase, e.g. "Software Engineer III – AI Enablement", "Senior Data Scientist, GTM". Manager, intern and executive phrases still drop it.
- **Audit tool:** `.venv/bin/python tools/filter_audit.py --show 20` lists every stored job the filters drop, grouped by the rule that dropped it. Run it after any filter change to spot real roles being filtered out.
- **Levels:**
  - `EXCLUDED_LEVEL_KEYWORDS = ()`, so all levels are kept.
  - To drop staff/principal again, set it to `ABOVE_SENIOR_LEVEL_KEYWORDS`.
- **US check:**
  - API country filters where the site has them; otherwise location text (`companies/json_api.is_us_location`) or Workday job paths (`companies/workday.is_us_posting`).
  - "Toronto, ON, CA" is treated as Canada.

Widening a filter does not resend old jobs: every listed job is already saved as seen, matching or not. It
applies to new postings from then on. To also get recent jobs the old filter dropped, see "Widen filters" below.

## Companies (44)

Every run reads each company's full listing; the page limits in each company file only need to exceed the site's page count.

| Slug | Company | Source | Pages | Site-side filter |
|---|---|---|---|---|
| `amazon` | Amazon | amazon.jobs `search.json` | all / all | US (`normalized_country_code`), full-time, non-manager, 6 tech categories, newest |
| `apple` | Apple | search page embedded JSON | 2 / 90 | US, Software & Services teams |
| `cvs` | CVS Health | jobs.cvshealth.com | 2 / 6 | keyword search |
| `cvs_wd` | CVS Health (Workday) | Workday | 2 / 6 | tech job family; shares IDs with `cvs` |
| `goldman-sachs` | Goldman Sachs | higher.gs.com | 2 / 30 | Analyst/Associate/VP, US offices |
| `google` | Google | careers page JSON | 5 / 25 | US, EARLY/MID/ADVANCED |
| `lyft` | Lyft | CareerPuck API | 1 / 1 | eng, data, security departments; US cities |
| `meta` | Meta | GraphQL | 1 / 1 | full-time, US offices, newest |
| `salesforce` | Salesforce | Workday | 3 / 6 | US |
| `uber` | Uber | jobs.uber.com API (in-page fetch) | all | Engineer + Science teams, US |
| `nvidia` | NVIDIA | Workday | 6 / 60 | US |
| `hp` | HP | Workday | 3 / 50 | US |
| `samsung` | Samsung | Workday | 3 / 50 | US |
| `cisco` | Cisco | Workday | 5 / 50 | US from job path |
| `disney` | Disney | Workday | 3 / 50 | US from job path |
| `paypal` | PayPal | Workday | 3 / 50 | US from job path |
| `intel` | Intel | Workday | 3 / 50 | US from job path |
| `yahoo` | Yahoo | Workday | 3 / 50 | US |
| `redhat` | Red Hat | Workday | 3 / 50 | US |
| `capitalone` | Capital One | Workday (wd12) | 5 / 50 | US from job path |
| `paloalto` | Palo Alto Networks | Workday `panwexternalcareers` | 4 / 50 | US from job path |
| `adobe` | Adobe | Workday `external_experienced` | 20 / 50 | US; not sorted newest-first, so all pages are read |
| `jpmc` | JPMorgan Chase | Oracle Recruiting Cloud | 4 / 40 | US, newest |
| `dell` | Dell | Oracle Recruiting Cloud | 2 / 40 | US, newest |
| `ford` | Ford | Oracle Recruiting Cloud | 2 / 40 | US, newest |
| `amex` | American Express | Oracle Recruiting Cloud | 2 / 40 | US, newest |
| `oracle` | Oracle | Oracle Recruiting Cloud `CX_45001` | 4 / 90 | US, newest |
| `ibm` | IBM | ibm.com search API | 3 / 20 | US, Entry Level + Professional |
| `amd` | AMD | iCIMS Jibe API | 6 / 60 | US, newest |
| `paramount` | Paramount | SuccessFactors HTML | 2 / 10 | US (client-side), newest |
| `netflix` | Netflix | Eightfold API | 3 / 40 | US, newest |
| `microsoft` | Microsoft | Eightfold PCSX (in-page fetch) | 8 / 60 | US, individual contributor, full-time, newest |
| `doordash` | DoorDash | Greenhouse `doordashusa` | all | US |
| `reddit` | Reddit | Greenhouse | all | US |
| `stripe` | Stripe | Greenhouse | all | US offices |
| `databricks` | Databricks | Greenhouse | all | US |
| `zscaler` | Zscaler | Greenhouse | all | US |
| `godaddy` | GoDaddy | Greenhouse | all | US |
| `pinterest` | Pinterest | Greenhouse | all | US |
| `snowflake` | Snowflake | Ashby | all | US |
| `cerebras` | Cerebras | Ashby | all | US |
| `atlassian` | Atlassian | atlassian.com careers listings JSON | all | US (location text) |
| `intuit` | Intuit | jobs.intuit.com (Radancy) results | all (~6 pages; not sorted by date) | US country facet |
| `spotify` | Spotify | Lever | all | US |

**Not possible:** Tesla. Its careers site returns 403 Access Denied to automation.

**Known behaviour:**
- Workday's wd1/wd5 data centers have maintenance windows (seen Saturday around 06:00 UTC).
- During one, requests redirect to an outage page, and several Workday companies send "broken" alerts that recover on their own.
- Capital One (wd12) is not affected.

## Configuration

### GitHub repository secrets
- `TELEGRAM_BOT_TOKEN`: bot token from @BotFather.
- `TELEGRAM_CHAT_ID`: target chat.

### External trigger (cron-job.org)
- **Job:** every 10 minutes, `POST https://api.github.com/repos/nishalcr/Job_Notifier/actions/workflows/scrape.yml/dispatches` with body `{"ref":"main"}`.
- **Headers:** `Authorization: Bearer <fine-grained PAT>`, `Accept: application/vnd.github+json`.
- **Token:** the PAT needs Actions read/write on this repo only. Note its expiry date and renew it before then.

### Environment variables (`config.py`, `health.py`)

| Variable | Default | Meaning |
|---|---|---|
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | — | Telegram destination (required) |
| `COMPANIES` | `apple` locally; all 44 in the workflows | Comma-separated slugs to scrape |
| `ALERT_TIMEZONE` | `America/Phoenix` | Time shown in message headers |
| `MAX_SEEN_JOBS` | `50000` | Seen-job cap per company |
| `HEALTH_FAILURE_THRESHOLD` | `3` | Consecutive failures before a "broken" alert |
| `PAGE_LOAD_TIMEOUT` | `15000` | Playwright page load timeout (ms) |
| `JOB_CARD_TIMEOUT` | `8000` | Selector wait timeout (ms) |
| `SCRAPE_ARTIFACTS_DIR` | `artifacts/` | Where failure diagnostics are saved |

Tunables in code:
- `scraper.py`: `CONCURRENCY = 8`, `COMPANY_TIMEOUT_SECONDS = 360`, `MAX_ALERT_AGE_DAYS = 30`, `FLOOD_KNOWN_SHARE = 0.1`, `FLOOD_MIN_JOBS = 50`.
- `notifier.py`: `MAX_MESSAGE_CHARS = 3800`.
- `details.py`: `TIME_BUDGET_SECONDS = 150`, `MAX_JOBS_PER_RUN = 40`.
- Each company file sets its pages per run with `default_max_pages`.

### Workflows

| File | Purpose | Trigger | Timeout |
|---|---|---|---|
| `scrape.yml` | Regular run: alert on new jobs, commit `seen_jobs/` | cron-job.org every 10 min | 18 min (scraper step 14) |
| `full-scrape.yml` | Seed `seen_jobs/` without alerts | manual | 90 min |
| `send-recent.yml` | Send matching jobs posted on a given day, even if already seen | manual (`companies`, `posted_on`) | 15 min |

When adding a company, update the slug list in **both** `scrape.yml` places (input default and `COMPANIES` fallback) and in `full-scrape.yml`.

## Runbooks

### Local setup
```bash
cd ~/Documents/Projects/Job_Notifier
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
```
Use `.venv/bin/python`; the system Python has no Playwright.

### Check status
```bash
gh run list -R nishalcr/Job_Notifier -w scrape.yml -L 10
git pull && cat seen_jobs/_health.json        # {} means every company is healthy
```
Don't bulk-download hundreds of run logs. That trips GitHub's API rate limit for about an hour, which also blocks cron-job.org's trigger (same account).

### Add a company
1. Find its job system and check the API from your machine:
   - Workday: `POST https://<host>/wday/cxs/<tenant>/<site>/jobs`.
   - Greenhouse: `boards-api.greenhouse.io/v1/boards/<board>/jobs`.
   - Others: Ashby, Lever, Oracle, Eightfold.
2. Create `companies/<slug>.py` using the shared builder (`workday_company`, `greenhouse_company`, `oracle_hcm_company`, `ashby_company`, `lever_company`, `eightfold_company`). Register it in `companies/registry.py`.
3. Test locally that it returns US jobs and that the matching titles look right.
4. Make sure its page limit (`default_full_scrape_max_pages`) is above the site's page count.
5. Add the slug to `scrape.yml` and `full-scrape.yml` and push. Its first run saves the current jobs without alerts; alerts start from the run after.

### Widen filters or search scope
1. Change `companies/filters.py` (or the company's site filter), add the titles to `tests/test_filters.py`, and run the tests.
2. Run `.venv/bin/python tools/filter_audit.py --show 20` to check nothing real is still dropped.
3. Push. New postings that match are alerted from the next run.
4. Optional: recent jobs the old filter dropped are already saved as seen and will not be alerted. To get them,
   remove those keys from `seen_jobs/<slug>.json` (jobs first seen in the last few days that now pass the filter)
   and commit; the next run alerts them if they were posted within 30 days.

A wider *site-side* search (for example a removed category filter) brings in jobs never saved before. The next run
alerts those posted within 30 days and saves older ones quietly. If many jobs appear at once while the saved ones are
still listed, that is a real catch-up, not a flood.

### Catch up on jobs a fix now matches
`send_recent.py --unseen --company <slugs>` reads deeper than a regular run and sends every matching job not in the seen store, then marks it seen. It needs `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, and you must commit `seen_jobs/` afterwards. Regular runs now do this automatically for jobs posted in the last 30 days, so this is rarely needed.

### Catch up on jobs that were seeded without alerts
Run **Send Jobs Posted On A Day** (`send-recent.yml`) with the companies and a date, or locally:
```bash
.venv/bin/python send_recent.py --company microsoft --posted-on 2026-10-23
```

### Runs stopped arriving
1. Check `gh run list`. If nothing has run in the last 20 minutes, the trigger is the problem.
2. Check the cron-job.org execution history for the job, and whether the job was auto-disabled after failures.
3. Check the PAT expiry date. A 401 means the token expired; a 403 rate limit usually clears within an hour.
4. Start a run by hand: `gh workflow run scrape.yml -R nishalcr/Job_Notifier`.

### A company sends "broken"
1. Look at `last_error` in `seen_jobs/_health.json` and the run's `scraper-diagnostics` artifact.
2. Test the company locally: `.venv/bin/python scraper.py --company <slug>`. With no `.env`, this skips Telegram but still updates local seen state, so don't commit those files.
3. If it is a Workday maintenance redirect, wait. It recovers on its own.

## Change history (this fork)
- **2026-09-27:**
  - Revived the original 10 companies.
  - Uber moved to an in-page API fetch.
  - Added health alerts.
  - Switched to the cron-job.org trigger.
- **2026-09/10:** grew to 37 companies through shared Workday, Oracle, Greenhouse, Ashby, Lever and Eightfold adapters.
- **2026-10-01:**
  - Scope widened to SWE, data, ML and AI at all levels.
  - Amazon switched to `search.json`.
- **2026-10-08:**
  - Added Pinterest, Palo Alto Networks and Adobe.
  - Added the duplicate protections above.
- **2026-10-29:** added Oracle and Cerebras.
- **2026-10-30:** added Atlassian and Intuit. Found runs missing jobs below the first pages (Amazon order, Workday backdated posts). Redesigned: every run reads every company's full list in parallel and compares it with the saved jobs; flood guard, per-company time limit, retries, tests. Salesforce and CVS (Workday) moved to the Workday API. Same-title rule removed. Filter audit: plurals, typos, scientist/researcher titles, Cisco Technical Leader, core-role override; 20 missed jobs from the previous week re-sent.
- **2026-10-23:**
  - One message per run.
  - Job details (pay, experience, work type, team, ID).
  - Apple switched to embedded JSON.
