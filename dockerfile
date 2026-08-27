# Selenium + Pytest automation for the portfolio website.
# This is what Docker runs in the confirmed pipeline: Jenkins (deployment
# job) builds this image with the selected branch's code, then the
# execution job (via the Execution API) runs it with the right params.

FROM python:3.11-slim

# Chromium + matching chromedriver from Debian's own repos - versions are
# guaranteed compatible with each other, no manual version-pinning needed.
# This also means no network call to download a driver at container
# start time (unlike webdriver-manager, which is used for local dev instead).
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV HEADLESS=true
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

# BASE_URL has no default on purpose - the pipeline's Execution API is
# expected to pass it in per run (see utils/config.py). Running the image
# without it will hit the placeholder URL in config.py and fail loudly,
# rather than silently testing the wrong site.

# The reports directory is what gets volume-mounted in the real pipeline -
# a new image build can wipe the container's filesystem, so reports need
# to land somewhere that survives outside it.
VOLUME ["/app/reports"]

# run_all_tests.py passes through any extra args, so `docker run <image> -m navigation`
# runs just that marker group instead of the full suite.
ENTRYPOINT ["python", "run_all_tests.py"]
CMD []