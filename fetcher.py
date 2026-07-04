"""Fetches full Bravos Research article text using an authenticated browser session.

The article pages are subscriber-gated. Rather than reverse-engineer Bravos'
login flow, we drive a persistent Chromium profile: the user logs in once by
hand (see README), and the session cookies are reused for every subsequent
fetch until they expire.
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

import config

LOGIN_URL = "https://bravosresearch.com/login/"
LOGIN_MARKER_RE = None  # set if a reliable "you must log in" string is found


class ArticleFetcher:
    def __init__(self, profile_dir: str = config.BROWSER_PROFILE_DIR):
        self.profile_dir = Path(profile_dir)
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = None
        self._context = None

    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            str(self.profile_dir),
            headless=True,
        )
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._context:
            self._context.close()
        if self._playwright:
            self._playwright.stop()

    def ensure_logged_in(self) -> bool:
        """Returns False if the session looks logged out (needs manual login)."""
        page = self._context.new_page()
        try:
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
            logged_in = page.locator("text=Log Out").count() > 0 or page.locator(
                "text=My Account"
            ).count() > 0
            return logged_in
        finally:
            page.close()

    def fetch_article_text(self, url: str) -> str:
        page = self._context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            body = page.locator("article").first
            if body.count() == 0:
                body = page.locator("main").first
            if body.count() == 0:
                return page.locator("body").inner_text()
            return body.inner_text()
        finally:
            page.close()


def manual_login(profile_dir: str = config.BROWSER_PROFILE_DIR):
    """Launches a visible browser so the user can log in once; session is saved
    to profile_dir and reused headlessly afterwards."""
    Path(profile_dir).mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(profile_dir, headless=False)
        page = context.new_page()
        page.goto(LOGIN_URL)
        print("Log in to Bravos Research in the opened browser window, then press Enter here...")
        input()
        context.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "login":
        manual_login()
    else:
        print("Usage: python fetcher.py login")
