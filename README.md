# Java Jobs → Telegram Channel Bot

Finds Java-family jobs every hour and posts each new one to a Telegram channel.
No backend, no server, no cost — it runs as a GitHub Actions cron job and stores
its state (`seen_jobs.json`) in the repo itself.

Covers core Java / Spring, full-stack Java + Angular, and Java + AI/ML roles.
Every post is tagged with detected skills (`#aws`, `#angular`, `#ai`, `#spring`, …)
and carries a **📋 View all jobs** button linking to an auto-updated Telegraph page.

## How it works

```
hourly cron → fetch sources → filter Java-family → drop already-seen
            → refresh Telegraph "all jobs" page → post up to 5 new jobs
            → commit updated state back to the repo
```

Sources (all free, no API keys): Remotive, Arbeitnow, Jobicy, RemoteOK.

## Setup (one-time, ~5 min)

1. **Create the bot** — message [@BotFather](https://t.me/BotFather), `/newbot`, copy the token.
2. **Create the channel** and add the bot as an **admin** with permission to post.
3. **Find the channel id** — use `@your_channel_username`, or the numeric `-100…` id.
4. **Add repository secrets** (Settings → Secrets and variables → Actions):
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHANNEL_ID`
   - `TELEGRAPH_ACCESS_TOKEN` — leave unset on the first run; the log prints a new
     token, which you then save as this secret so the "all jobs" page stays stable.
5. **First run** — Actions → *Post Java jobs* → *Run workflow*, tick **bootstrap**.
   This marks the current backlog as seen so the channel starts clean.
6. Done — the hourly schedule takes over automatically.

## Local development

```bash
pip install -r requirements.txt

# Print formatted messages instead of posting (no secrets needed):
python -m src.main --dry-run

# Run the tests:
pip install pytest
pytest
```

## Project layout

| Path | Purpose |
|------|---------|
| `src/fetchers/` | One module per job source, each returns normalized `Job`s |
| `src/filter.py` | Java-family matching + JavaScript false-positive guard |
| `src/tagger.py` | Skill hashtag detection + profile-match badge |
| `src/state.py` | Dedupe state (`seen_jobs.json`), pruned after 60 days |
| `src/poster.py` | Telegram message formatting + sending |
| `src/telegraph_page.py` | Regenerates the "all jobs" page each run |
| `src/main.py` | Orchestration + `--dry-run` / `--bootstrap` flags |
| `.github/workflows/jobs.yml` | Hourly cron that runs the bot and commits state |

## Tuning

- Posts per run: `MAX_POSTS_PER_RUN` in `src/main.py` (default 5).
- Schedule: the `cron` line in `.github/workflows/jobs.yml`.
- Filter/skills: keyword lists in `src/filter.py` and `src/tagger.py`.
