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

def run_linkedin(playwright, config: dict, logger: logging.Logger, headless: bool = False, action: str = "run") -> None:
    """Runs the LinkedIn Easy Apply automation."""
    import linkedin_actions as actions

    # Manual login is assumed from here on, credentials aren't required.
    username = config.get("linkedin_username")
    password = config.get("linkedin_password")

    logger.info("Closing existing Chrome instances...")
    os.system("taskkill /F /IM chrome.exe")
    time.sleep(1)

    # Force visible browser for manual login
    if action == "manual_login":
        headless = False

    # Mask the headless user agent
    real_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=os.path.join(os.getcwd(), "ChromeProfile"),
        channel="chrome",
        headless=headless,
        user_agent=real_user_agent,
        ignore_default_args=["--mute-audio", "--hide-scrollbars", "--enable-automation"],
        no_viewport=True,
        args=[
            "--start-maximized",
            "--profile-directory=Default",
            "--disable-extensions",
            "--disable-gpu",
            "--disable-blink-features=AutomationControlled",
        ],
    )

    # Stealth: hide webdriver
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    # Safely get or create the first page
    if context.pages:
        page = context.pages[0]
    else:
        page = context.new_page()

    logger.info("Navigating to LinkedIn...")
    try:
        page.goto("https://www.linkedin.com/", wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        logger.warning(f"Timeout during navigation, continuing anyway: {e}")

    if action == "check_login":
        status, user_name = actions.is_already_logged_in(page)
        name_str = f"|{user_name}" if user_name else ""
        print(f"LOGIN_STATUS: {'SUCCESS' if status else 'FAILED'}{name_str}")
        context.close()
        return

    if action == "logout":
        actions.logout(page)
        print("LOGOUT_STATUS: SUCCESS")
        context.close()
        return

    if action == "manual_login":
        print("Waiting for user to log in manually...")
        # Check every 2 seconds if feed is detected
        status, _ = actions.is_already_logged_in(page)
        while not status:
            time.sleep(2)
            status, _ = actions.is_already_logged_in(page)
        print("LOGIN_STATUS: SUCCESS")
        context.close()
        return

    status, _ = actions.is_already_logged_in(page)
    if not status:
        actions.login(page, username, password)
        
    job_records = []
    try:
        actions.search_jobs(page, config)
        job_records = actions.apply_to_jobs(page, config)
    except Exception as e:
        logger.error(f"Critical execution error during LinkedIn processing: {e}")

    logger.info("Generating PDF report...")
    from report_generator import generate_pdf_report
    report_path = generate_pdf_report("linkedin", job_records)
    logger.info(f"Execution report saved to: {report_path}")

    # Save to database
    import database
    applied = sum(1 for j in job_records if j.get("status") == "Applied")
    ignored = sum(1 for j in job_records if j.get("status") == "Ignored")
    failed = sum(1 for j in job_records if j.get("status") == "Failed")
    db_status = "Completed" if not failed else "Completed with Errors"
    
    # Check if Email Alerts are enabled
    email_status = "Not Configured/Disabled"
    if config.get("email_alerts") is True:
        import emailer
        logger.info("Email Alerts enabled. Sending report...")
        subject = f"LinkedIn Job Application Run: {db_status}"
        body = f"""
        <h2>LinkedIn Automation Run Completed</h2>
        <p><strong>Status:</strong> {db_status}</p>
        <ul>
            <li><strong>Applied:</strong> {applied}</li>
            <li><strong>Ignored:</strong> {ignored}</li>
            <li><strong>Failed:</strong> {failed}</li>
        </ul>
        <p>Please find the detailed PDF report attached.</p>
        """
        success = emailer.send_email(subject, body, report_path)
        email_status = "Sent" if success else "Failed"

    database.save_run("linkedin", db_status, applied, ignored, failed, report_path, email_status)

    logger.info("LinkedIn automation finished.")
    context.close()


def run_naukri(playwright, config: dict, logger: logging.Logger, headless: bool = False, action: str = "run") -> None:
    """Runs the Naukri job apply automation."""
    import naukri_actions as actions

    # Manual login is assumed from here on, credentials aren't required.
    username = config.get("naukri_username")
    password = config.get("naukri_password")

    logger.info("Closing existing Chrome instances...")
    os.system("taskkill /F /IM chrome.exe")
    # Wait longer than LinkedIn — Naukri's persistent profile lock can take a moment to release
    time.sleep(3)

    # Force visible browser for manual login
    if action == "manual_login":
        headless = False

    # Mask the headless user agent
    real_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=os.path.join(os.getcwd(), "ChromeProfile"),
        channel="chrome",
        headless=headless,
        user_agent=real_user_agent,
        ignore_default_args=["--mute-audio", "--hide-scrollbars", "--enable-automation"],
        no_viewport=True,
        args=[
            "--start-maximized",
            "--profile-directory=Default",
            "--disable-extensions",
            "--disable-gpu",
            "--disable-blink-features=AutomationControlled",
        ],
    )

    # Stealth: hide webdriver
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    # Safely get or create the first page
    if context.pages:
        page = context.pages[0]
    else:
        page = context.new_page()

    logger.info("Navigating to Naukri...")
    try:
        page.goto("https://www.naukri.com/", wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        logger.warning(f"Timeout during navigation, continuing anyway: {e}")

    if action == "check_login":
        status, user_name = actions.is_already_logged_in(page)
        name_str = f"|{user_name}" if user_name else ""
        print(f"LOGIN_STATUS: {'SUCCESS' if status else 'FAILED'}{name_str}")
        context.close()
        return

    if action == "logout":
        actions.logout(page)
        print("LOGOUT_STATUS: SUCCESS")
        context.close()
        return

    if action == "manual_login":
        print("Waiting for user to log in manually...")
        status, _ = actions.is_already_logged_in(page)
        while not status:
            time.sleep(2)
            status, _ = actions.is_already_logged_in(page)
        print("LOGIN_STATUS: SUCCESS")
        context.close()
        return

    status, _ = actions.is_already_logged_in(page)
    if not status:
        actions.login(page, username, password)
        
    job_records = []
    try:
        actions.search_jobs(page, config)
        job_records = actions.apply_to_jobs(page, config)
    except Exception as e:
        logger.error(f"Critical execution error during Naukri processing: {e}")

    logger.info("Generating PDF report...")
    from report_generator import generate_pdf_report
    report_path = generate_pdf_report("naukri", job_records)
    logger.info(f"Execution report saved to: {report_path}")

    # Save to database
    import database
    applied = sum(1 for j in job_records if j.get("status") == "Applied")
    ignored = sum(1 for j in job_records if j.get("status") == "Ignored")
    failed = sum(1 for j in job_records if j.get("status") == "Failed")
    db_status = "Completed" if not failed else "Completed with Errors"
    
    # Check if Email Alerts are enabled
    email_status = "Not Configured/Disabled"
    if config.get("email_alerts") is True:
        import emailer
        logger.info("Email Alerts enabled. Sending report...")
        subject = f"Naukri Job Application Run: {db_status}"
        body = f"""
        <h2>Naukri Automation Run Completed</h2>
        <p><strong>Status:</strong> {db_status}</p>
        <ul>
            <li><strong>Applied:</strong> {applied}</li>
            <li><strong>Ignored:</strong> {ignored}</li>
            <li><strong>Failed:</strong> {failed}</li>
        </ul>
        <p>Please find the detailed PDF report attached.</p>
        """
        success = emailer.send_email(subject, body, report_path)
        email_status = "Sent" if success else "Failed"
        
    database.save_run("naukri", db_status, applied, ignored, failed, report_path, email_status)

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
    parser.add_argument(
        "--action",
        default="run",
        choices=["run", "check_login", "manual_login", "logout"],
        help="Action to perform. Default is 'run'.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode",
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
            run_linkedin(playwright, config, logger, args.headless, args.action)
        elif platform == "naukri":
            run_naukri(playwright, config, logger, args.headless, args.action)


if __name__ == "__main__":
    main()
