# Portfolio Website Automation

A Selenium + Pytest test suite for my portfolio website, wired into a full CI/CD pipeline: Docker, a distributed Selenium Grid, Jenkins (both a standard pipeline and a PR-gating Multibranch pipeline), a container registry, vulnerability scanning, and Slack/email notifications.

This started as a plain POM-based test suite. It's grown into a working example of most of what a real CI/CD pipeline actually involves, including the bugs that came with it.

## What's actually in this pipeline

```
GitHub (push / PR)
    │
    ├── portfolio-automation (Pipeline, Poll SCM every 5 min)
    │       └── tests master after merge → email to stakeholders
    │
    └── portfolio-automation-pr (Multibranch Pipeline, periodic scan)
            └── tests every open PR before merge → Slack alert to #ci-alerts

Both jobs run the same Jenkinsfile:

Checkout
    ↓
Prepare (parallel)
    ├── Deployment Job   → docker build, tagged :<build-number> and :latest
    └── Execution Job    → execution_api/build_command.py constructs pytest args
    ↓
Push Image            → ghcr.io/beinghumantester/portfolio-automation
    ↓
Security Scan         → Trivy (CRITICAL/HIGH, report-only for now)
    ↓
Health Check          → site reachability + Selenium Grid readiness
    ↓
Run Tests             → docker compose run, against the Grid
    ↓
Reports & Notify      → Allure + HTML + JUnit, Slack (PRs) or email (master)
```

A pipeline-wide lock (Lockable Resources) stops both jobs from ever running at the same time, since they'd otherwise collide on the same Grid ports.

## Structure

```
portfolio-automation/
├── Jenkinsfile            # the whole pipeline described above
├── Dockerfile              # lean - no browser bundled, Grid handles that
├── docker-compose.yml      # selenium-hub + chrome-node + firefox-node + tests
├── .env.example            # documents every env var; copy to .env for local runs
├── .gitignore
├── run_all_tests.py        # single entry point - runs every test file in order
├── conftest.py            # driver fixture (local Chrome or remote Grid), screenshot-on-failure
├── pytest.ini              # markers, reruns, html/allure/junit config
├── requirements.txt
├── execution_api/
│   └── build_command.py    # simulates the real "Execution API" - builds pytest args from TEST_MARKER
├── trigger_api/
│   └── app.py              # Flask front-door: stakeholders POST here (Postman etc.) to trigger a Jenkins build without Jenkins access
├── pages/                  # Page Object Model
│   ├── base_page.py         # shared wait/click/find/class-toggle/url-wait helpers
│   ├── landing_page.py       # nav tabs + sidebar social links + subscribe CTA
│   ├── subscribe_modal.py    # EmailOctopus popup form
│   └── cv_page.py            # STILL A PLACEHOLDER - see below
├── tests/
│   ├── test_navigation.py
│   ├── test_social_links.py
│   ├── test_subscribe_popup.py
│   └── test_cv_download.py
└── utils/
    └── config.py            # BASE_URL, timing constants, browser/env config, loads .env
```

## Running it locally (no Docker, no Grid)

```bash
cp .env.example .env
# edit .env with a real BASE_URL
pip install -r requirements.txt
python run_all_tests.py
```

Runs every test file in a fixed order (navigation → social links → CV → subscribe popup, fastest checks first, so a broken build fails fast before burning time on the popup tests' built-in waits). Plain `pytest` also works if you don't need that ordering.

Run a specific group:
```bash
pytest -m navigation
pytest -m modal
pytest -m links
```

HTML report generates at `reports/report.html`; failure screenshots land in `reports/screenshots/`; JUnit XML at `reports/junit.xml`.

## Running it the way the pipeline does (Docker + Selenium Grid)

```bash
docker build -t portfolio-automation .
docker compose up -d selenium-hub chrome-node firefox-node
docker compose run --rm tests
docker compose down -v
```

`conftest.py`'s driver fixture automatically switches to remote mode when `SELENIUM_REMOTE_URL` is set, connecting to the Grid instead of launching a local browser. Set `BROWSER=firefox` to run against the Firefox node instead of Chrome, no code changes needed.

## The CI/CD pieces, briefly

- **Image versioning** - every build is tagged with its Jenkins build number, not just `:latest`, so any past build is traceable to an exact image.
- **GHCR push** - images are pushed to GitHub Container Registry so they exist beyond one machine's Docker daemon. Pushes re-authenticate and retry per tag (a real `unauthorized` bug on the second push of a session led to this).
- **Trivy security scan** - runs right after the image is built, reports CRITICAL/HIGH CVEs. Currently report-only (`--exit-code 0`) while a baseline gets established; a one-line flag flip turns it into an actual gate.
- **Health check before testing** - checks the site itself is reachable, then polls the Grid hub's `/status` endpoint until it reports ready, before spending time running the suite against something that might not even be up.
- **Auto-retry for flaky tests** - `pytest-rerunfailures`, up to 2 retries with a 3s delay, before a test is counted as a real failure.
- **PR-based gating** - the Multibranch job tests every pull request automatically, before merge, and posts the result straight to Slack. The regular Pipeline job still handles `master`, with results going to email instead - different audiences, different urgency.

## What's covered (real locators, confirmed against actual site HTML)

- **Navigation** - About (`/`), Publications (`/publications`), Blogs (`/posts`), Speaking (`/talks`), Playground (`/projects`), AI In Testing (`/ai-in-testing`), CV (`/cv`), TWIL (`/twil`).
- **Sidebar links** - GitHub, YouTube, Ministry of Testing, LinkedIn, and the `mailto:` email link, matched against real `href` values.
- **Subscribe popup** - confirmed end-to-end against the site's own script:
  - Auto-triggers 5 seconds after first visit, via `setTimeout` on the `astro:page-load` event.
  - Toggles visibility through an `active` class + opacity transition, not DOM add/remove - tests check the class directly.
  - Gated by a `sessionStorage` flag (`newsletterAutoShown`) that blocks the *automatic* popup from firing twice in one session, but doesn't disable manually clicking "Subscribe" in the nav, which still opens it every time. Both behaviors have dedicated tests.
  - A honeypot field exists for spam protection; a regression test confirms automation never fills it.

## Known issues (documented, not silently ignored)

- **EmailOctopus vendor bug** - the popup widget has its own ungated ~10s auto-show timer in its own `form.js`, completely independent of the site's `sessionStorage` gate. It reopens the popup regardless of whether the user already dismissed it. Two tests are marked `xfail` for this specific, confirmed vendor behavior - fix belongs in the widget's own settings, not this suite.
- **CV page locators are still a placeholder** (`pages/cv_page.py`) - the real `/cv` page HTML has never been shared, so `DOWNLOAD_CV_BUTTON` is a guessed selector, not a confirmed one. Replace it once the actual markup is available.
- **Subscribe form submission** isn't tested end-to-end - the form has an invisible reCAPTCHA that would block a real submission in headless/CI runs.
- **Publication/Blogs/Speaking/Playground/AI In Testing page content** (individual articles or talk links) isn't covered yet - only tab navigation is. Straightforward to extend with a dedicated `pages/*.py` class per page.
