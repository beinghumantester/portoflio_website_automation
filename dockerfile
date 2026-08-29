# Selenium + Pytest automation for the portfolio website - Grid mode.
# The browser no longer runs inside this image; tests connect out to a
# Selenium Grid (hub + Chrome/Firefox nodes, see docker-compose.yml).
# That's what keeps this image lean - no Chromium/chromedriver install
# needed here at all, unlike the earlier standalone version of this file.

FROM python:3.11-slim

# Links this image to its source repo on GHCR automatically on every push,
# so "Connect Repository" doesn't need to be clicked manually each time.
LABEL org.opencontainers.image.source=https://github.com/beinghumantester/portoflio_website_automation

ENV HEADLESS=true
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages \
    --timeout 120 --retries 5 \
    -r requirements.txt

COPY . .

# BASE_URL has no default on purpose - it's expected to be passed in per
# run (see utils/config.py and docker-compose.yml).

VOLUME ["/app/reports"]

ENTRYPOINT ["python", "run_all_tests.py"]
CMD []