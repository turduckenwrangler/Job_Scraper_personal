# 🧪 Environmental / Toxicology Job Scraper — Dr. Scott Coffin

Three GitHub Actions pipelines that scrape **environmental toxicology, risk &
exposure assessment, environmental health, water quality, microplastics/PFAS &
emerging-contaminants, chemical safety / regulatory, and supporting data-science
roles** across **California**, commit the results to this repo, and surface them
in the [`triage.html`](#interactive-triage-dashboard--triagehtml) dashboard.

> Originally built by [Ernesto Diaz](https://github.com/ernestod1998) as a Bay
> Area ML-engineer scraper; retargeted here for Dr. Scott Coffin's field
> (environmental/regulatory toxicology). See his profile at
> [scottcoff.in](https://scottcoff.in).

## What It Does

### 1. Priority-employer digest — daily, last 24h
Hits LinkedIn's public guest endpoint for California env/tox roles posted in the
last 24 hours, then post-filters to a **priority-employer allowlist** derived
from `BIOTECH_COMPANY_NAMES` in `scrape_jobs.py` — environmental/tox consulting
firms (Ramboll, Exponent, Gradient, ToxStrategies, Tetra Tech, ICF, Integral,
Geosyntec…), research institutes & NGOs (SCCWRP, SFEI, Silent Spring, EDF, NRDC,
EWG, Health Effects Institute, RTI, Battelle…), agencies (US EPA, CalEPA/OEHHA,
State Water Board, CARB, DTSC, NIEHS…), water utilities, universities, and
product-safety teams in industry. Add to that list to expand coverage.

Output goes to `jobs.json`, `jobs.md`, and `jobs.html`. Each run dedupes against
the previously-committed `jobs.json`, so the output surfaces only postings new
since the last run.

> A direct-ATS probe path (`CURATED_BIOTECHS`) also exists but is **empty by
> default** — environmental/tox employers overwhelmingly use iCIMS/Taleo/
> SuccessFactors rather than the public Greenhouse/Workday JSON endpoints the
> original biotech version relied on. The LinkedIn + Indeed keyword watchers
> (which need no employer slug) are the primary sources.

### 2. LinkedIn watcher — hourly, last 1h
Hits LinkedIn's public guest endpoint for **California** roles posted in the last
hour across the env/tox search terms, dedupes by job ID, and sorts by recency.
Output goes to `linkedin_jobs.json`, `linkedin_jobs.md`, and `linkedin_jobs.html`.

Runs hourly at :17 PT (8am–8pm) via native GitHub cron, with the in-repo
watchdog (`linkedin_watch_backup.yml` at :33) re-dispatching missed slots. A
block guard preserves the previous results when LinkedIn returns zero cards
across every term (rate-limited run).

> ⚠️ Uses the unauthenticated public guest endpoint only — **never** signs in
> with a user account and does not use LinkedIn cookies, tokens, or credentials.

### 3. Indeed watcher — hourly, last 24h
Uses [`python-jobspy`](https://pypi.org/project/python-jobspy/) (Indeed's RSS and
Publisher API were deprecated in 2026 and the site sits behind Cloudflare;
JobSpy uses Indeed's mobile-app API internally). Searches California. Output goes
to `indeed_jobs.json`, `indeed_jobs.md`, and `indeed_jobs.html`, deduped against
the previous run. Runs at :47 PT, offset from LinkedIn's :17 slot.

## Keywords Matched

A title is included if it contains any of these (case-insensitive). Multi-word
phrases match as substrings; single tokens are word-bounded (so list full words).
Full list lives in `KEYWORDS` in `scrape_jobs.py`:

**Toxicology:** `toxicologist`, `toxicology`, `ecotoxicologist`, `environmental
toxicolog`, `regulatory toxicolog`, `computational toxicolog`, `aquatic
toxicolog`, `research toxicolog`

**Risk / exposure / hazard:** `risk assess`, `risk assessor`, `human health
risk`, `ecological risk`, `exposure scien`, `exposure assess`, `hazard assess`,
`dose-response`, `pharmacokinetic`, `toxicokinetic`

**Environmental science / health / chemistry:** `environmental scien`,
`environmental health`, `environmental chemist`, `environmental engineer`,
`environmental epidemiolog`, `public health`, `epidemiologist`

**Water / contaminants:** `water quality`, `water resources`, `drinking water`,
`microplastic`, `nanoplastic`, `pfas`, `emerging contaminant`, `contaminant`,
`pollution`, `remediation`

**Chemical safety / regulatory / stewardship:** `chemical safety`, `product
steward`, `regulatory scien`, `regulatory affairs`, `chemical regulatory`

**Ecology / sustainability / data / policy / academia:** `ecologist`,
`sustainability scien`, `research scientist`, `senior scientist`, `principal
scientist`, `health scientist`, `science director`, `data scientist`, `science
policy`, `professor`, `faculty`

**Excluded (junior / not worth a senior scientist's time):** titles containing
`intern`, `internship`, `co-op`, `trainee`, `apprentice`, `technician`,
`research/lab/teaching assistant`, `undergraduate`, `postdoc`, `work-study`,
`volunteer`, or `fellowship` are dropped everywhere. (Unlike the original, which
dropped *senior* titles — Dr. Coffin is a senior IC, so senior/principal/lead/
director roles are **kept**.)

## Geographic Scope

- **LinkedIn** searches California statewide (`geoId=102095887`). Swap to
  `103644278` for the whole US, or a metro geoId to narrow.
- **Indeed** searches `location="California"`. Narrow to `"Sacramento, CA"` with
  `distance=50` to focus on the home region.
- The curated/legacy ATS path filters with `is_target_location()` /
  `TARGET_LOCATIONS` (Sacramento region + Bay Area + SoCal + Central Coast +
  remote).

## Output Files

| File | Source | Description |
|---|---|---|
| `jobs.json` / `.md` / `.html` | Priority-employer digest | Allowlisted env/tox employer roles, last 24h, deduped against the previous run |
| `linkedin_jobs.json` / `.md` / `.html` | LinkedIn watcher | California roles posted in the last 1h, deduped |
| `indeed_jobs.json` / `.md` / `.html` | Indeed watcher | Indeed-sourced California roles, last 24h, deduped |
| `all_jobs.json` | accumulator | Cumulative 14-day master (feeds the dashboard + triage) |
| `scores.json` | triage agent | Optional fit verdicts keyed by job URL |

### Interactive triage dashboard — `triage.html`

A single-file dashboard hosted on GitHub Pages that merges the latest source
JSONs into one filterable cockpit: search; source / role / seniority filters
(roles classified as Toxicology, Risk/Exposure, Water, Contaminants,
Environmental Health, Environmental Science, Policy/Regulatory, Data Science,
Academic); save / applied / dismiss buttons persisted in localStorage; top-
companies and role-mix charts; and an "export saved as Claude prompt" action.

**View it (after enabling Pages — see Deployment):**
`https://scottcoffin.github.io/Job_Scraper/triage.html`

The dashboard fetches the JSON files from the same repo at view time, so it
always reflects the latest committed scrape. To run locally:
```bash
python -m http.server 8000
# then visit http://localhost:8000/triage.html
```
Opening from `file://` won't work — the dashboard needs same-origin HTTP to
`fetch()` the source JSONs.

## Setup

### Run manually

From the **Actions** tab → Run workflow:
- *Priority Employers Digest* → priority-employer LinkedIn allowlist, last 24h
- *LinkedIn Env/Tox Watcher* → general California LinkedIn, last 1h
- *Indeed Env/Tox Watcher* → California Indeed via python-jobspy, last 24h

Or locally:
```bash
python scrape_jobs.py --biotech-only   # priority-employer digest (allowlist)
python scrape_jobs.py --linkedin-only  # general env/tox LinkedIn, last 1h
python scrape_jobs.py --indeed-only     # general env/tox Indeed, last 24h
```
The LinkedIn/priority pipelines use only the standard library. Indeed requires
`pip install -r requirements.txt` (single dep: `python-jobspy`).

### Optional: nightly fit-scoring agent (`triage.yml`)

`triage_agent.py` scores each new role against your profile with the Claude API.
It is **optional** and needs three repo secrets (**Settings → Secrets and
variables → Actions**):

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `CANDIDATE_PROFILE` | Short profile text (your background/targets — kept out of the public repo) |
| `CANDIDATE_RESUME` | Resume / CV text (kept out of the public repo) |

Paste your CV text into `CANDIDATE_RESUME`. Without these secrets, leave
`triage.yml` and `evals.yml` disabled (Actions → ⋯ → Disable workflow) — the
scrapers and dashboard work fully without them; `scores.json` is optional.

> Note: `eval_triage.py` still contains the original ML-candidate golden cases.
> They only matter if you run the triage agent; rewrite them for your domain (or
> keep `evals.yml` disabled) once you've finalized your profile.

## Repo Structure

```
├── scrape_jobs.py                  # All scraping logic + KEYWORDS / search terms / allowlist
├── triage_agent.py                 # Optional nightly fit-scoring agent (Claude API)
├── eval_triage.py                  # Golden-case evals for the triage agent (legacy ML cases)
├── requirements.txt                # python-jobspy (Indeed only)
├── jobs.{json,md,html}             # Priority-employer digest (last 24h)
├── linkedin_jobs.{json,md,html}    # LinkedIn watcher (last 1h)
├── indeed_jobs.{json,md,html}      # Indeed watcher (last 24h)
├── all_jobs.json                   # Cumulative 14-day master
├── scores.json                     # Triage verdicts (optional)
├── triage.html                     # Interactive dashboard
└── .github/workflows/
    ├── scrape_jobs.yml             # Daily — priority-employer digest
    ├── linkedin_watch.yml          # Hourly :17 PT — general LinkedIn (last 1h)
    ├── indeed_watch.yml            # Hourly :47 PT — Indeed (last 24h)
    ├── linkedin_watch_backup.yml   # Watchdog :33 PT — re-dispatches missed runs
    ├── triage.yml                  # Nightly — optional fit scoring (needs secrets)
    └── evals.yml                   # Triage-agent evals (optional)
```

## Tuning the search

Everything you'd adjust lives near the top of `scrape_jobs.py`:
- `KEYWORDS` — title match terms.
- `EXCLUDED_SENIORITY_RE` — junior/student titles to drop.
- `LINKEDIN_SEARCH_TERMS` / `WORKDAY_SEARCH_TERMS` — queries sent to the boards.
- `BIOTECH_COMPANY_NAMES` — the priority-employer allowlist (for `jobs.json`).
- `TARGET_LOCATIONS` + the LinkedIn `geoId` + the Indeed `location`.
