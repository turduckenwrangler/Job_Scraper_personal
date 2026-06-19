# Fork Setup Guide

Turn this repo into **your** job tracker in about 10 minutes.  
You get the full scraping + scoring + dashboard engine; all your customizations live only in your fork so you can pull upstream code improvements without conflicts.

---

## 1. Fork the repo

Click **Fork** on GitHub. Enable GitHub Actions when prompted (Actions are disabled on new forks by default).

---

## 2. Create your config

```bash
cp config.example.json config.json
cp scoring_profile.example.json scoring_profile.json
```

Edit **`config.json`** — this single file controls everything:
- `profile.title` / `profile.subtitle` — dashboard heading and location tag
- `keywords.include` / `keywords.exclude` — job-title filter terms
- `search_terms` — queries sent to each job board
- `locations` — where you want to work
- `employers.exclude` — companies to skip

Edit **`scoring_profile.json`** — controls how roles are ranked:
- `fit_terms` — keyword → weight pairs that reflect your background
- `poor_fit_terms` — keyword → penalty pairs for off-target roles
- `settings.standout_threshold` — minimum score for a push notification

> **Tip:** See `docs/cv-to-config-prompt.md` for a prompt that generates both files from your CV automatically.

---

## 3. Commit your config to your fork

```bash
git add config.json scoring_profile.json
git commit -m "chore: personalize config and scoring profile"
git push
```

These files are gitignored in the upstream repo so upstream can never overwrite them.

---

## 4. Add GitHub Actions secrets

In your fork → **Settings → Secrets and variables → Actions**, add:

| Secret | Required | Description |
|--------|----------|-------------|
| `ANTHROPIC_API_KEY` | For triage scoring | Anthropic API key |
| `CANDIDATE_PROFILE` | For triage scoring | Your career summary (paste the text) |
| `CANDIDATE_RESUME` | For triage scoring | Your resume text |
| `PUSHOVER_TOKEN` | For notifications | Pushover app token |
| `PUSHOVER_USER` | For notifications | Pushover user key |

Only `ANTHROPIC_API_KEY` + the two profile secrets are required for the core workflow. Pushover is optional.

Optional variable (under **Variables**, not Secrets):

| Variable | Default | Description |
|----------|---------|-------------|
| `NOTIFY_MIN_FIT` | `40` | Minimum fit score to trigger a push notification |

---

## 5. Enable GitHub Pages (optional — for the dashboard)

In your fork → **Settings → Pages**, set source to **GitHub Actions** or the `main` branch `/` root.  
The triage dashboard (`triage.html`) is generated and committed by CI — it will be live at:

```
https://<your-github-username>.github.io/<your-fork-name>/triage.html
```

---

## Pulling upstream improvements

Your `config.json`, `scoring_profile.json`, and all job data files are gitignored by upstream, so they never appear in upstream commits. Pulling is always clean:

```bash
git remote add upstream https://github.com/ScottCoffin/Job_Scraper.git
git fetch upstream
git merge upstream/main
```

Only code files (`*.py`, `*.yml`, docs, etc.) change — your customizations are untouched.
