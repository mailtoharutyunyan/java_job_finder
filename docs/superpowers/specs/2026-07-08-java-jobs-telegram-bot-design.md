# Java Jobs → Telegram Channel Bot — Design

**Date:** 2026-07-08
**Status:** Approved pending user review

## Goal

Automatically find Java-family jobs (core Java backend, full-stack Java + Angular, Java + AI/ML, cloud/AWS) every hour and post each new job as a formatted message to a Telegram channel — with zero self-hosted backend. Every post carries a button opening an auto-updated "all current jobs" page.

## Architecture

A single Python project in a GitHub repository, executed hourly by GitHub Actions cron (`0 * * * *`). There is no server: the Telegram bot never receives updates; it only calls the Bot API `sendMessage` to post into the channel (bot must be a channel admin). State lives in a JSON file committed back to the repo by the workflow.

Note: GitHub cron runs can start a few minutes late under load — acceptable here. Public repos have unlimited Actions minutes; private repos get 2,000/month (this uses ~25 min/day).

## Components

```
telegram_ajva_job/
├── .github/workflows/jobs.yml   # hourly cron, runs script, commits state
├── src/
│   ├── main.py                  # orchestration + --dry-run / --bootstrap flags
│   ├── fetchers/                # one module per source
│   │   ├── remotive.py
│   │   ├── arbeitnow.py
│   │   ├── jobicy.py
│   │   └── remoteok.py
│   ├── filter.py                # Java-family matching + JS false-positive guard
│   ├── tagger.py                # skill hashtag detection
│   ├── poster.py                # Telegram message formatting + sending
│   └── telegraph_page.py        # regenerates the "all jobs" Telegraph page
├── seen_jobs.json               # dedupe state (committed by workflow)
├── tests/                       # filter + dedupe unit tests
└── requirements.txt             # requests only (stdlib otherwise)
```

### Job sources

- **Phase 1 (no API keys):** Remotive, Arbeitnow, Jobicy, RemoteOK — free public JSON APIs, mostly remote roles (worldwide/EU).
- **Phase 2 (optional, later):** Adzuna and/or JSearch (RapidAPI) with free-tier keys for on-site roles in configurable countries.

Each fetcher normalizes its source into one schema:
`{id, title, company, location, salary, url, tags, description_snippet, source, published_at}`.

### Filter (`filter.py`)

A job **passes** if title/tags/description match any of:

- Core Java: `java`, `spring`, `spring boot`, `jvm`, `j2ee`, `jakarta`
- Full-stack Java: `java` combined with `angular` / frontend terms
- AI/ML with Java: `java` combined with `ai`, `machine learning`, `ml engineer`, `llm`, `genai`

A job is **rejected** when "java" only appears as part of JavaScript signals: title terms like `javascript`, `js`, `node`, `node.js`, `react`, `typescript` without an independent Java signal. All seniority levels pass. Match mode is "all Java jobs" — Angular/AWS/AI are **not required**, only tagged.

### Skill tagging (`tagger.py`)

Detects skills in job text and appends hashtags to each post: `#java #fullstack #angular #aws #ai #spring #kotlin #kubernetes #docker #kafka #microservices #remote #senior` etc. Enables Telegram's in-channel hashtag search.

### Dedupe

`seen_jobs.json` maps a stable job key (SHA-256 of normalized job URL) → first-seen timestamp. Entries older than 60 days are pruned. The workflow commits the updated file after each successful run; state only advances after posts succeed, so a failed run is retried naturally next hour.

### Poster (`poster.py`)

One message per job:

```
☕ Full Stack Java Developer
🏢 Acme Corp
📍 Remote (EU)
💰 €70k–90k

🔗 Apply: https://…

#java #fullstack #angular #aws #spring
```

- Inline keyboard on every message: `[ 📋 View all jobs ]` → URL button to the Telegraph page.
- Cap: **5 posts per hourly run**; overflow rolls to the next hour (oldest first).
- 3-second delay between sends (Telegram rate limits).
- `--bootstrap` mode: first run marks the existing backlog as seen without posting.

### All-jobs page (`telegraph_page.py`)

Each run regenerates a Telegraph page (Telegram's publishing service, `telegra.ph` — opens as Instant View inside Telegram, no account/backend needed; the API returns an access token on first `createAccount` call, stored as a GitHub secret after first run). Page lists all active jobs (seen within last N days, default 14), grouped by date, each with company/location/apply link. Page URL is stable, so the button URL never changes.

## Data flow

Hourly cron → fetch all sources (each independently; one failing source doesn't kill the run) → normalize → filter Java-family → drop seen → sort oldest-first → post up to 5 with buttons → regenerate Telegraph page → commit `seen_jobs.json`.

## Secrets (GitHub Actions secrets)

- `TELEGRAM_BOT_TOKEN` — from @BotFather
- `TELEGRAM_CHANNEL_ID` — channel `@username` or numeric id
- `TELEGRAPH_ACCESS_TOKEN` — created on first run, then stored
- (Phase 2) `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` / `RAPIDAPI_KEY`

## Error handling

- Per-fetcher try/except with logged warnings; run continues with remaining sources.
- Telegram send failures: retry once, then skip the job (stays unseen → retried next run).
- Telegraph page failure is non-fatal (posts still go out).

## Testing

- Unit tests: filter (Java vs JavaScript cases, full-stack and AI combos), tagger, dedupe pruning.
- `--dry-run` flag prints formatted messages instead of posting — verifiable locally with no secrets.

## One-time user setup (~5 min)

1. Create bot via @BotFather → token.
2. Create the Telegram channel; add the bot as admin (post permission).
3. Create GitHub repo, push code, add secrets.
4. Run workflow once manually with `--bootstrap`, then enable hourly schedule.

## Out of scope (v1)

- Interactive bot commands (would need a webhook — revisit with Cloudflare Workers if ever wanted).
- On-site/country-specific aggregators (Phase 2).
- Job expiry detection beyond the 14-day page window.
