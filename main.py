# main.py
# Unified entry point for the Job Apply Automation.
#
# Usage:
#   python main.py --platform linkedin
#   python main.py --platform naukri
#
import argparse
import time
import json
import logging
import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright


# ---------------------------------------------------------------------------
# Shared logger setup (platform-aware)
# ---------------------------------------------------------------------------

def cleanup_old_logs(logs_dir: str, keep_count: int) -> None:
    """Keeps only the keep_count most recent log files in logs_dir."""
    try:
        if not os.path.exists(logs_dir):
            return
        log_files = [
            os.path.join(logs_dir, f)
            for f in os.listdir(logs_dir)
            if f.endswith(".log")
        ]
        # Sort by modification time (newest first)
        log_files.sort(key=os.path.getmtime, reverse=True)
        if len(log_files) > keep_count:
            for old_file in log_files[keep_count:]:
                try:
                    os.remove(old_file)
                except Exception:
                    pass
    except Exception:
        pass


def setup_logger(platform: str, max_logs: int = 5) -> logging.Logger:
    """Creates a logger that writes to both console and a timestamped log file inside a logs folder.
    Cleans up old logs keeping only the specified maximum.
    """
    logger_name = f"{platform.capitalize()}Automation"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    # Ensure logs folder exists
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Clean up old logs before creating a new one
    cleanup_old_logs(logs_dir, max_logs)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(logs_dir, f"{platform}_run_{timestamp}.log")
    
    log_format = logging.Formatter(
        "%(asctime)s - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    fh = logging.FileHandler(log_filename)
    fh.setLevel(logging.INFO)
    fh.setFormatter(log_format)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(log_format)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def load_config(config_path: str) -> dict:
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Config file not found: {config_path}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Platform runners
# ---------------------------------------------------------------------------

def run_linkedin(playwright, config: dict, logger: logging.Logger) -> None:
    """Runs the LinkedIn Easy Apply automation."""
    import linkedin_actions as actions

    username = config.get("linkedin_username")
    password = config.get("linkedin_password")
    if not username or not password:
        logger.error("linkedin_username or linkedin_password missing in config.json")
        return

    logger.info("Closing existing Chrome instances...")
    os.system("taskkill /F /IM chrome.exe")
    time.sleep(1)

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=r"C:\Users\swapn\ChromeAutomationProfile",
        channel="chrome",
        headless=False,
        ignore_default_args=["--mute-audio", "--hide-scrollbars"],
        no_viewport=True,
        args=[
            "--start-maximized",
            "--profile-directory=Default",
            "--disable-extensions",
            "--disable-gpu",
        ],
    )

    page = context.pages[0]
    logger.info("Navigating to LinkedIn...")
    page.goto("https://www.linkedin.com/")
    page.wait_for_load_state("domcontentloaded")

    if not actions.is_already_logged_in(page):
        actions.login(page, username, password)
    actions.search_jobs(page)
    actions.apply_to_jobs(page, config)

    logger.info("LinkedIn automation finished.")
    context.close()


def run_naukri(playwright, config: dict, logger: logging.Logger) -> None:
    """Runs the Naukri job apply automation."""
    import naukri_actions as actions

    username = config.get("naukri_username")
    password = config.get("naukri_password")
    if not username or not password:
        logger.error("naukri_username or naukri_password missing in naukri_config.json")
        return

    logger.info("Closing existing Chrome instances...")
    os.system("taskkill /F /IM chrome.exe")
    # Wait longer than LinkedIn — Naukri's persistent profile lock can take a moment to release
    time.sleep(3)

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=r"C:\Users\swapn\ChromeAutomationProfile",
        channel="chrome",
        headless=False,
        ignore_default_args=["--mute-audio", "--hide-scrollbars"],
        no_viewport=True,
        args=[
            "--start-maximized",
            "--profile-directory=Default",
            "--disable-extensions",
            "--disable-gpu",
        ],
    )

    # Safely get or create the first page
    if context.pages:
        page = context.pages[0]
    else:
        page = context.new_page()

    logger.info("Navigating to Naukri...")
    page.goto("https://www.naukri.com/")
    page.wait_for_load_state("domcontentloaded")

    if not actions.is_already_logged_in(page):
        actions.login(page, username, password)
    actions.search_jobs(page, config)
    actions.apply_to_jobs(page, config)

    logger.info("Naukri automation finished.")
    context.close()




# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Job Apply Automation — LinkedIn & Naukri",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--platform",
        required=True,
        choices=["linkedin", "naukri"],
        help=(
            "Which platform to automate:\n"
            "  linkedin  ->  LinkedIn Easy Apply automation\n"
            "  naukri    ->  Naukri Apply automation"
        ),
    )
    parser.add_argument(
        "--config",
        default=None,
        help=(
            "Path to the config JSON file.\n"
            "Defaults: config.json (linkedin), naukri_config.json (naukri)"
        ),
    )
    args = parser.parse_args()

    platform = args.platform

    # Resolve config path
    if args.config:
        config_path = args.config
    elif platform == "linkedin":
        config_path = "config.json"
    else:
        config_path = "naukri_config.json"

    # Load config first to read max_log_files count
    config = load_config(config_path)
    max_logs = config.get("max_log_files", 5)

    logger = setup_logger(platform, max_logs)

    logger.info(f"Starting automation for platform: {platform.upper()}")
    logger.info(f"Using config: {config_path}")

    with sync_playwright() as playwright:
        if platform == "linkedin":
            run_linkedin(playwright, config, logger)
        elif platform == "naukri":
            run_naukri(playwright, config, logger)


if __name__ == "__main__":
    main()
