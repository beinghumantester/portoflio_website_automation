# Portfolio Website Automation (Selenium + Pytest)

POM-based Selenium automation for the portfolio website, built as the first
step toward the CI/CD pipeline (Jenkins → Docker → Pytest+Selenium
→ reports) confirmed with the team.

## Structure

```
portfolio-automation/
├── run_all_tests.py      # single entry point - runs every test file in order
├── conftest.py          # driver fixture, screenshot-on-failure hook
├── pytest.ini            # markers, html report config
├── requirements.txt
├── pages/                # Page Object Model
│   ├── base_page.py       # shared wait/click/find/class-toggle helpers
│   ├── landing_page.py    # nav tabs + sidebar social links + subscribe CTA
│   ├── subscribe_modal.py # EmailOctopus popup form
│   └── cv_page.py         # STILL A PLACEHOLDER - see below
├── tests/
│   ├── test_navigation.py
│   ├── test_social_links.py
│   ├── test_subscribe_popup.py
│   └── test_cv_download.py
└── utils/
    └── config.py          # BASE_URL, timing constants, browser/env config
```

## Setup

```bash
pip install -r requirements.txt
export BASE_URL="https://your-real-portfolio-url.com"
python run_all_tests.py
```

This runs every test file in one go, in a fixed order (navigation → social
links → CV → subscribe popup - fastest checks first, so a broken build fails
fast before burning time on the popup tests' built-in waits). Equivalent to
running `pytest` directly, just with explicit ordering and one file to call.

Extra args pass through, e.g. `python run_all_tests.py -k "cv"`.

Plain `pytest` (no ordering, still runs everything) also works if you don't
need the explicit order:

```bash
pytest
```

HTML report generates at `reports/report.html`; failure screenshots land in
`reports/screenshots/`.

Run a specific group:

```bash
pytest -m navigation
pytest -m modal
pytest -m links
```

## What's covered (real locators, confirmed against actual site HTML)

- **Navigation** — About (`/`), Publications (`/publications`), Blogs
  (`/posts`), Speaking (`/talks`), Playground (`/projects`), AI In Testing
  (`/ai-in-testing`), CV (`/cv`), TWIL (`/twil`). Two of these (Playground,
  AI In Testing) weren't in the original spec but exist on the live site.
- **Sidebar links** — GitHub, YouTube, Ministry of Testing, LinkedIn, and
  the `mailto:` email link, matched against real `href` values.
- **Subscribe popup** — confirmed end-to-end against the site's own script:
  - Auto-triggers **5 seconds** after first visit (not 10 - corrected once
    the actual script was shared), via `setTimeout` on the `astro:page-load`
    event.
  - Toggles visibility through an `active` class + opacity transition, not
    DOM add/remove - tests check the class directly rather than plain
    Selenium visibility, which would false-positive here.
  - Gated by a `sessionStorage` flag (`newsletterAutoShown`) that blocks the
    *automatic* popup from firing twice in one session - but does **not**
    disable manually clicking the "Subscribe" nav button, which still opens
    it every time. Both behaviors have dedicated tests.
  - The flag lives in `sessionStorage`, so it survives a page reload in the
    same tab (tested), but resets in a new tab/session (not tested - would
    need a fresh browser context).
  - A honeypot field (`hpc4b27b6e...`) exists for spam protection; a
    regression test confirms automation never fills it.
  - The form has an **invisible reCAPTCHA**. `SubscribeModal.submit()` is
    implemented but not exercised by any test expecting a success state -
    that would likely be blocked in headless/CI runs. Flagging this now so
    it's not a surprise once this suite is wired into Jenkins.

## What's NOT covered yet

- **CV page** (`pages/cv_page.py`) — still a placeholder locator
  (`[data-testid='download-cv']`). The `/cv` page HTML hasn't been shared
  yet (only `/` and the popup markup have been). `test_cv_download.py` will
  fail until this is replaced with a real selector.
- Actual subscribe form **submission** success/error states (blocked by
  reCAPTCHA in automated runs - see above).
- Publication/Blogs/Speaking/Playground/AI In Testing **page content**
  (e.g. individual article or talk links) - only tab navigation is covered.
  Easy to extend later with a `pages/*.py` class per page.

## Next step: Docker

This is what gets containerized in the pipeline. A `Dockerfile` needs to:
1. Use a Python base image
2. `pip install -r requirements.txt`
3. Install a matching Chrome/Chromium binary and driver (or point to a
   Selenium Grid container instead of bundling the driver locally)
4. Run `pytest` as the container's entrypoint, with `BASE_URL` and other
   params passed in as environment variables - this is what the Execution
   API in the confirmed pipeline would set dynamically per run
