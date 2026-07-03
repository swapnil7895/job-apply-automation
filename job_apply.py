# job_apply.py
from playwright.sync_api import Playwright, sync_playwright
from utils import load_config, logger
import linkedin_actions as actions
import os

def run(playwright: Playwright) -> None:
    config = load_config()
    username = config.get("linkedin_username")
    password = config.get("linkedin_password")
    if not username or not password:
        return

    logger.info("Closing all Chrome instances...")
    os.system("taskkill /F /IM chrome.exe")
    logger.info("Chrome instances closed")

    context = playwright.chromium.launch_persistent_context(
            user_data_dir=r"C:\Users\swapn\ChromeAutomationProfile",
            channel="chrome",
            headless=False,
            ignore_default_args=["--mute-audio", "--hide-scrollbars"],
            no_viewport=True,
            args=[
                "--start-maximized",
                "--profile-directory=Default",
                "--disable-extensions",            # Bypasses heavy daily extensions that hang automation
                "--disable-gpu"                   # Prevents GPU rendering context locks
            ]
        )


    page = context.pages[0]    

    logger.info("Navigating to LinkedIn...")
    page.goto("https://www.linkedin.com/")
    page.wait_for_load_state("domcontentloaded")

    # Sequence execution passing the context
    if not actions.is_already_logged_in(page):
        actions.login(page, username, password)
    actions.search_jobs(page)
    actions.apply_to_jobs(page, config)

    logger.info("Script finished execution safely.")
    context.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)