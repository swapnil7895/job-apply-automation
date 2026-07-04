# linkedin_actions.py
import time
from utils import logger

def is_already_logged_in(page) -> bool:
    """Checks the current screen state to see if a valid session is already active.
    
    Returns True if logged in, False if on a login/landing page.
    """
    logger.info("Checking authentication state...")
    try:
        # 1. Check if we are already on the feed URL
        time.sleep(5)
        logger.info(f"URL - {page.url}")
        if "linkedin.com/feed" in page.url:
            logger.info("Session active: Detected feed URL path.")
            return True

        # 2. Look for a core feed element (like the global navigation bar or search input)
        # We give it a short 3-second timeout so it doesn't hang if we aren't logged in
        global_nav = page.get_by_test_id("typeahead-input")
        if global_nav.is_visible(timeout=3000):
            logger.info("Session active: Found home feed search input element.")
            return True

        # 3. Double check via your main feed URL selector pattern matching if needed
        # If the sign-in button or link is visible, we are definitely NOT logged in
        sign_in_link = page.get_by_role("link", name="Sign in", exact=True)
        if sign_in_link.is_visible(timeout=1000):
            logger.info("Session expired: 'Sign In' button detected on landing grid.")
            return False

    except Exception as check_err:
        logger.debug(f"State assessment element check bypassed: {check_err}")
    
    logger.info("No active session detected. Proceeding with authentication flow.")
    return False

def login(page, username, password) -> None:
    """Handles routing to sign-in panel and entering credentials securely"""
    logger.info("At login func")
    page.get_by_role("link", name="Sign in", exact=True).click()
    page.wait_for_load_state("domcontentloaded")

    try:
        logger.info("Filling credentials...")
        email_field = page.locator("input[type='email'][autocomplete*='username']")
        try:
            email_field.wait_for(state="visible", timeout=5000)
            email_field.fill(username)
        except Exception:
            page.get_by_role("textbox", name="Email or phone").fill(username)

        logger.info("Email is filled")
        password_field = page.locator("input[type='password']")
        try:
            logger.info("pwd field is visible")
            password_field.fill(password)
        except Exception:
            logger.warning("Dynamic password locator missed, utilizing standard fallback textbox")
            page.get_by_role("textbox", name="Password").fill(password)

        page.get_by_role("button", name="Sign in", exact=True).click()
        page.wait_for_url("https://www.linkedin.com/feed/**", timeout=15000)
        logger.info("Successfully logged in!")
        
    except Exception as login_err:
        logger.warning("Auto-login interrupted (Verification check or UI update detected).")
        input("Please manually log in to your feed view, then press Enter here: ")

def search_jobs(page) -> None:
    """Handles the keyword insertion and applying filter settings"""
    logger.info("Executing job search and target filters...")
    
    search_input = page.get_by_test_id("typeahead-input")
    search_input.wait_for(state="visible", timeout=10000)
    time.sleep(20)
    search_input.fill("python")    
    search_input.press("Enter")
    time.sleep(5)
    logger.info("entered python")
    
    page.wait_for_load_state("domcontentloaded")
    time.sleep(3)

    logger.info("Applying Search Filters...")
    # 'Jobs' filter
    try:
        try: page.get_by_role("radio", name="Filter by Jobs").click(timeout=3000)
        except: page.locator("button:has-text('Jobs')").first.click(timeout=5000)
        time.sleep(5)
    except Exception as e:
        logger.warning(f"Jobs filter error (ignoring): {e}")
    
    # 'Easy Apply' filter
    try:
        try: page.get_by_role("radio", name="Filter by Easy Apply").click(timeout=3000)
        except: page.locator("button:has-text('Easy Apply')").first.click(timeout=5000)
        time.sleep(2)
    except Exception as e:
        logger.warning(f"Easy Apply filter error (ignoring): {e}")
    
    # 'Date posted' filter
    try:
        try: page.get_by_role("button", name="Filter by Date posted").click(timeout=3000)
        except: page.locator("button:has-text('Date posted')").first.click(timeout=5000)
        time.sleep(1)
        
        try: page.get_by_role("radio", name="Past week").click(timeout=3000)
        except: page.locator("label:has-text('Past week'), span:has-text('Past week')").first.click(timeout=5000)
        time.sleep(1)
        
        try: page.get_by_role("button", name="Show results").click(timeout=3000)
        except: page.locator("button:has-text('Show results'), span:has-text('Show results')").first.click(timeout=5000)
        time.sleep(4)
    except Exception as e:
        logger.warning(f"Date posted filter error (ignoring): {e}")

def fill_dynamic_fields(page, config) -> None:
    """Dynamically detects and fills input fields in the modal."""
    logger.info("Scanning for dynamic input fields...")
    
    # 1. Text inputs and Selects via raw tags
    inputs = page.locator("input, textarea, select").all()
    for el in inputs:
        try:
            if not el.is_visible():
                continue
                
            tag_name = el.evaluate("el => el.tagName").lower()
            
            if tag_name == "select":
                try:
                    el.scroll_into_view_if_needed(timeout=1000)
                    el.select_option(label="Yes", timeout=2000)
                except:
                    options = el.locator("option").all()
                    if len(options) > 1:
                        val = options[1].get_attribute("value")
                        if val:
                            el.select_option(val, timeout=2000)
            
            elif tag_name in ["input", "textarea"]:
                input_type = (el.get_attribute("type") or "").lower()
                
                # Skip non-text inputs
                if input_type in ["radio", "checkbox", "hidden", "submit", "button", "file"]:
                    continue
                    
                if el.is_editable():
                    val = el.input_value()
                    error_id = el.get_attribute("aria-describedby")
                    has_error = False
                    if error_id:
                        try:
                            has_error = page.locator(f"#{error_id}").is_visible(timeout=500)
                        except: pass
                    
                    if not val or has_error:
                        el.scroll_into_view_if_needed(timeout=1000)
                        name_attr = el.get_attribute("name") or ""
                        id_attr = el.get_attribute("id") or ""
                        aria_label = el.get_attribute("aria-label") or ""
                        label_text = el.evaluate("el => { const l = document.querySelector(`label[for='${el.id}']`); return l ? l.innerText : (el.parentElement ? el.parentElement.innerText : ''); }")
                        
                        combined = (name_attr + id_attr + aria_label + label_text).lower()
                        
                        if "ctc" in combined or "salary" in combined:
                            is_expected = "expect" in combined
                            short_val = config.get("expected_ctc", "23") if is_expected else config.get("ctc", "16.2")
                            full_val = config.get("expected_ctc_full", "2300000") if is_expected else config.get("ctc_full", "1620000")
                            
                            if has_error:
                                # If we had an error on the short value, try the full value
                                el.fill(full_val, timeout=2000)
                            else:
                                # Try short value first unless it says lakh
                                if "lakh" in combined:
                                    el.fill(short_val, timeout=2000)
                                else:
                                    el.fill(short_val, timeout=2000)
                        elif "year" in combined or "exp" in combined or "experience" in combined:
                            el.fill(config.get("total_exp", "5"), timeout=2000)
                        elif "location" in combined or "city" in combined:
                            el.fill(config.get("location", "Pune"), timeout=2000)
                            time.sleep(1.5)
                            el.press("ArrowDown")
                            time.sleep(0.5)
                            el.press("Enter")
                            time.sleep(0.5)
                        elif "linkedin" in combined or "website" in combined or "profile" in combined:
                            el.fill(config.get("linkedin_url", "https://www.linkedin.com/in/swapnil-dhamal-33b5b2220/"), timeout=2000)
                        else:
                            el.fill(config.get("total_exp", "5"), timeout=2000)
        except Exception as e:
            logger.debug(f"Input fill error: {e}")

    # 2. Radio Buttons (Inside fieldsets)
    fieldsets = page.locator("fieldset").all()
    for fs in fieldsets:
        try:
            if fs.is_visible():
                checked = fs.locator("input[type='radio']:checked").count()
                if checked == 0:
                    yes_radio = fs.locator("label").filter(has_text="Yes")
                    if yes_radio.count() > 0 and yes_radio.first.is_visible():
                        yes_radio.first.scroll_into_view_if_needed(timeout=1000)
                        yes_radio.first.click(timeout=2000)
                    else:
                        first_radio = fs.locator("label").first
                        if first_radio.is_visible():
                            first_radio.scroll_into_view_if_needed(timeout=1000)
                            first_radio.click(timeout=2000)
                    time.sleep(0.5)
        except Exception as e:
            logger.debug(f"Radio fill error: {e}")

def apply_to_jobs(page, config) -> list:
    """Finds all job cards using the custom DOM XPath, iterates through them, and handles Easy Apply.
    Returns a list of job processing records."""
    logger.info("Starting Job Application Loop")
    job_records = []
    
    custom_job_xpath = "div[componentkey^='job-card-component-ref']"

    try:
        page.locator(custom_job_xpath).first.wait_for(state="visible", timeout=15000)
    except Exception:
        logger.error("No job cards matching your custom XPath were found on the page.")
        return job_records

    # Scroll the job pane to load all jobs
    logger.info("Scrolling job pane to load all listings...")
    pane = page.locator("[componentkey='SearchResultsMainContent']")
    if pane.is_visible():
        for _ in range(5):
            pane.evaluate("el => el.scrollTo(0, el.scrollHeight)")
            time.sleep(1.5)
            
    time.sleep(3)

    job_cards = page.locator(custom_job_xpath).all()
    total_jobs = len(job_cards)
    logger.info(f"Successfully identified {total_jobs} job records via custom XPath.")


    for index, card in enumerate(job_cards):
        try:
            card.scroll_into_view_if_needed()
            card.click()
            time.sleep(3)
            
            # Now that the right pane has loaded, extract the title and company
            # We use href patterns because LinkedIn's CSS classes are randomized hashes
            title_element = page.locator("a[href*='/jobs/view/']").first
            company_element = page.locator("a[href*='/company/']").first
            
            raw_title = title_element.inner_text().strip() if title_element.count() > 0 and title_element.is_visible() else f"Job #{index + 1}"
            raw_company = company_element.inner_text().strip() if company_element.count() > 0 and company_element.is_visible() else "Unknown Company"
            
            job_title = f"{raw_title} at {raw_company}"
            logger.info(f"[{index + 1}/{total_jobs}] Processing: {job_title}")
            
            # Check if it explicitly says we already applied
            if page.locator("text='Application submitted'").is_visible():
                logger.info(" -> Skipping: Application submitted status detected.")
                job_records.append({"title": job_title, "status": "Ignored", "reason": "Already applied"})
                continue

            # Find the Easy Apply button
            # We first try the role="link" which Playwright originally recorded.
            easy_apply_trigger = page.get_by_role("link", name="Easy Apply to this job").first
            if not easy_apply_trigger.is_visible():
                # Fallback to general button search
                easy_apply_trigger = page.locator("button:has-text('Easy Apply')").first
            
            if easy_apply_trigger.is_visible():
                logger.info(" -> 'Easy Apply' found! Opening modal...")
                easy_apply_trigger.click()
                time.sleep(2)

                logger.info(" -> Processing form steps...")
                max_steps = 10
                for step_num in range(max_steps):
                    # Fill dynamic fields on the current step
                    fill_dynamic_fields(page, config)

                    next_btn = page.get_by_role("button", name="Continue to next step")
                    review_btn = page.get_by_role("button", name="Review your application")
                    submit_btn = page.get_by_role("button", name="Submit application")
                    
                    if next_btn.is_visible():
                        try: next_btn.scroll_into_view_if_needed(timeout=1000)
                        except: pass
                        next_btn.click()
                        time.sleep(2)
                    elif review_btn.is_visible():
                        try: review_btn.scroll_into_view_if_needed(timeout=1000)
                        except: pass
                        review_btn.click()
                        time.sleep(2)
                    elif submit_btn.is_visible():
                        try: submit_btn.scroll_into_view_if_needed(timeout=1000)
                        except: pass
                        logger.info(" -> Form completed. Submitting application...")
                        time.sleep(2)
                        submit_btn.click() 
                        time.sleep(3) # Wait a moment for submission to process
                        
                        # Handle the small success popup cross sign (Dismiss)
                        try:
                            dismiss_btn = page.locator("button[aria-label='Dismiss']").first
                            if dismiss_btn.is_visible():
                                logger.info(" -> Closing post-submission popup...")
                                dismiss_btn.click()
                                time.sleep(1)
                        except: pass
                        job_records.append({"title": job_title, "status": "Applied", "reason": "Success"})
                        break
                    else:
                        # If we can't click next, review, or submit, we might be stuck on a required field or at the end
                        logger.warning(" -> Stuck on form step. Attempting to close modal...")
                        try:
                            close_btn = page.locator("button[aria-label='Dismiss']").first
                            if close_btn.is_visible(timeout=1000):
                                close_btn.click()
                                time.sleep(1)
                                discard_btn = page.locator("button:has-text('Discard')").first
                                if discard_btn.is_visible(timeout=1000):
                                    discard_btn.click()
                                    time.sleep(1)
                        except Exception as e:
                            logger.error(f" -> Could not dismiss modal: {e}")
                        job_records.append({"title": job_title, "status": "Failed", "reason": "Stuck on form step"})
                        break

                not_now_btn = page.get_by_role("button", name="Not now")
                if not_now_btn.is_visible():
                    not_now_btn.click()
                    time.sleep(1)
            else:
                logger.info(" -> Skipping: Already applied or regular external application link.")
                job_records.append({"title": job_title, "status": "Ignored", "reason": "External apply / No Easy Apply btn"})

        except Exception as card_err:
            logger.error(f"Failed to process card index {index + 1}: {card_err}")
            job_records.append({"title": f"Job #{index + 1}", "status": "Failed", "reason": str(card_err)[:35]})
            continue

    logger.info("Finished processing all job listings on this page")
    return job_records