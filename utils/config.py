import os
from dotenv import load_dotenv

# Loads variables from a local .env file into the environment, if one
# exists. Safe to call even when there's no .env at all (e.g. in Docker/
# Jenkins, where BASE_URL etc. are passed in directly) - it just does
# nothing in that case. See .env.example for what this file should contain.
load_dotenv()

# TODO: replace with your actual deployed portfolio URL.
# Kept as an env var so the same code works locally and inside Docker/Jenkins
# (pass -e BASE_URL=... at run time, or set it in the Jenkins job/pipeline).
BASE_URL = os.getenv("BASE_URL", "https://your-portfolio-url.com")

# How long the site waits before auto-showing the subscribe popup on first
# visit. Confirmed from the site's own script (setTimeout(..., 5000)) -
# this is 5s, not the 10s originally assumed before the script was shared.
SUBSCRIBE_POPUP_DELAY_SECONDS = 5

# Small buffer so we don't race the popup's own timer.
SUBSCRIBE_POPUP_WAIT_BUFFER = 5

BROWSER = os.getenv("BROWSER", "chrome")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"