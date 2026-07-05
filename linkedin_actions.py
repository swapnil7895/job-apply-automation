import time
import intent_engine
from utils import logger

def is_already_logged_in(page) -> tuple[bool, str]:
    """Checks the current screen state to see if a valid session is already active.
    
    Returns (True, user_name) if logged in, (False, "") if on a login/landing page.
    """
    logger.info("Checking authentication state...")
    user_name = ""
    try:
        # 1. Check if we are already on the feed URL
        time.sleep(5)
        logger.info(f"URL - {page.url}")
        
        is_logged_in = False
        if "linkedin.com/feed" in page.url:
            logger.info("Session active: Detected feed URL path.")
            is_logged_in = True

        # 2. Look for a core feed element (like the global navigation bar or search input)
        # We give it a short 3-second timeout so it doesn't hang if we aren't logged in
        global_nav = page.get_by_test_id("typeahead-input")
        if not is_logged_in and global_nav.is_visible(timeout=3000):
            logger.info("Session active: Found home feed search input element.")
            is_logged_in = True
            
        if is_logged_in:
            try:
                # Array of possible locators for the user's name
                name_locators = [
                    page.locator(".t-16.t-black.t-bold"),
                    page.locator('a[href^="/in/"]').first,
                    page.locator('xpath=//*[@id="workspace"]/div/div/aside[1]/div/div/div/div[1]/div/div/div/div/a[1]/div/div[1]/div/p/span'),
                    page.locator('xpath=/html/body/div/div[2]/div[2]/div[2]/div/main/div/div/aside[1]/div/div/div/div[1]/div/div/div/div/a[1]/div/div[1]/div/p'),
                    page.locator('div[class*="fee11784"] p span')
                ]

                for n_loc in name_locators:
                    if n_loc.count() > 0 and n_loc.first.is_visible(timeout=1000):
                        text = n_loc.first.inner_text().strip()
                        # Avoid grabbing promotional banners
                        if text and "Premium" not in text and "Off" not in text and "\n" not in text:
                            user_name = text
                            break

                if not user_name:
                    # The aside panel often fails to render in headless mode,
                    # so the absolute easiest and most reliable way is grabbing
                    # the first image alt text (which is the nav profile photo).
                    for img_el in page.locator("img[alt]").all():
                        if img_el.is_visible(timeout=1000):
                            alt_text = img_el.get_attribute("alt")
                            # The user's name is usually the first image alt text, 
                            # while others have "View X's profile" or "avatar".
                            if alt_text and "view " not in alt_text.lower() and "icon" not in alt_text.lower() and "avatar" not in alt_text.lower():
                                user_name = alt_text.strip()
                                break
            except Exception as e:
                logger.warning(f"Failed to fetch user name: {e}")
            return True, user_name

        # 3. Double check via your main feed URL selector pattern matching if needed
        # If the sign-in button or link is visible, we are definitely NOT logged in
        sign_in_link = page.get_by_role("link", name="Sign in", exact=True)
        if sign_in_link.is_visible(timeout=1000):
            logger.info("Session expired: 'Sign In' button detected on landing grid.")
            return False, ""

    except Exception as check_err:
        logger.debug(f"State assessment element check bypassed: {check_err}")
    
    logger.info("No active session detected. Proceeding with authentication flow.")
    return False, ""

def logout(page) -> None:
    """Logs the user out by clearing cookies."""
    logger.info("Logging out from LinkedIn...")
    try:
        page.context.clear_cookies()
        page.goto("https://www.linkedin.com/m/logout/")
        time.sleep(2)
        logger.info("Logout successful.")
    except Exception as e:
        logger.error(f"Error during logout: {e}")

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

def search_jobs(page, config: dict) -> None:
    """Handles the keyword insertion and applying filter settings"""
    logger.info("Executing job search and target filters...")
    
    keywords = config.get("job_keywords", ["python"])
    keyword_str = keywords[0] if isinstance(keywords, list) and keywords else (keywords if isinstance(keywords, str) else "python")

    search_input = page.get_by_test_id("typeahead-input")
    search_input.wait_for(state="visible", timeout=10000)
    time.sleep(20)
    search_input.fill(keyword_str)    
    search_input.press("Enter")
    time.sleep(5)
    logger.info(f"entered {keyword_str}")
    
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
    if config.get("easy_apply", True):
        try:
            try: page.get_by_role("radio", name="Filter by Easy Apply").click(timeout=3000)
            except: page.locator("button:has-text('Easy Apply')").first.click(timeout=5000)
            time.sleep(2)
        except Exception as e:
            logger.warning(f"Easy Apply filter error (ignoring): {e}")
            
    # 'Remote' filter
    if config.get("remote_only", False):
        try:
            # First, try to see if 'Remote' is just a direct tag/pill toggle on the UI
            direct_clicked = False
            try:
                # LinkedIn often puts hidden text like '(1,000 results)' inside the label, so exact match fails.
                # Restricting to 'label' or 'button[aria-checked]' avoids clicking job cards.
                tag = page.locator("label:has-text('Remote'), button[aria-checked]:has-text('Remote'), button[aria-pressed]:has-text('Remote')").filter(visible=True).first
                if tag.is_visible(timeout=2000):
                    tag.click(timeout=2000)
                    time.sleep(3)
                    direct_clicked = True
            except:
                pass
                
            if not direct_clicked:
                dropdown_clicked = False
                for btn_name in ["Workplace type", "Workplace", "On-site/remote", "Remote"]:
                    try:
                        try: page.get_by_role("button", name=f"Filter by {btn_name}").click(timeout=2000)
                        except: page.locator(f"button:has-text('{btn_name}')").first.click(timeout=2000)
                        dropdown_clicked = True
                        break
                    except:
                        pass
                
                if dropdown_clicked:
                    time.sleep(1)
                    try:
                        try: page.locator("label:has-text('Remote')").filter(visible=True).first.click(timeout=2000)
                        except:
                            try: page.get_by_role("radio", name="Remote").click(timeout=2000)
                            except:
                                try: page.get_by_role("checkbox", name="Remote").click(timeout=2000)
                                except: page.locator("span:has-text('Remote')").filter(visible=True).first.click(timeout=2000)
                    except: pass
                    time.sleep(1)
                    try: page.locator("button:has-text('Show results'), span:has-text('Show results')").filter(visible=True).first.click(timeout=4000)
                    except: pass
                    time.sleep(4)

        except Exception as e:
            logger.warning(f"Remote filter error (ignoring): {e}")
    
    # 'Date posted' filter
    date_posted_val = config.get("date_posted", "Past week")
    if date_posted_val != "Any time":
        try:
            direct_clicked = False
            try:
                tag = page.locator(f"label:has-text('{date_posted_val}'), button[aria-checked]:has-text('{date_posted_val}'), button[aria-pressed]:has-text('{date_posted_val}')").filter(visible=True).first
                if tag.is_visible(timeout=2000):
                    tag.click(timeout=2000)
                    time.sleep(3)
                    direct_clicked = True
            except:
                pass
            
            if not direct_clicked:
                try: page.get_by_role("button", name="Filter by Date posted").click(timeout=3000)
                except: page.locator("button:has-text('Date posted')").first.click(timeout=5000)
                time.sleep(1)
                
                try: page.locator(f"label:has-text('{date_posted_val}')").filter(visible=True).first.click(timeout=3000)
                except:
                    try: page.get_by_role("radio", name=date_posted_val).click(timeout=3000)
                    except: page.locator(f"span:has-text('{date_posted_val}')").filter(visible=True).first.click(timeout=5000)
                time.sleep(1)
                
                try: page.locator("button:has-text('Show results'), span:has-text('Show results')").filter(visible=True).first.click(timeout=4000)
                except: pass
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
                        
                        response = intent_engine.resolve_intent(combined, field_type="text", profile=config)
                        answer = response.get("answer")
                        
                        if answer:
                            el.fill(answer, timeout=2000)
                        elif "linkedin" in combined or "website" in combined or "profile" in combined:
                            el.fill(config.get("linkedin_url", "https://www.linkedin.com/in/swapnil-dhamal-33b5b2220/"), timeout=2000)
                        else:
                            el.fill(config.get("total_exp", "5"), timeout=2000)
                            
                        # Special handling for autocomplete location drop downs if location intent was resolved
                        if answer == config.get("location", "Pune") and any(kw in combined for kw in ["location", "city"]):
                            time.sleep(1.5)
                            el.press("ArrowDown")
                            time.sleep(0.5)
                            el.press("Enter")
                            time.sleep(0.5)
        except Exception as e:
            logger.debug(f"Input fill error: {e}")

    # 2. Radio Buttons (Inside fieldsets)
    fieldsets = page.locator("fieldset").all()
    for fs in fieldsets:
        try:
            if fs.is_visible():
                checked = fs.locator("input[type='radio']:checked").count()
                if checked == 0:
                    fs_legend = fs.locator("legend").first
                    q_context = fs_legend.inner_text().strip().lower() if fs_legend.is_visible() else ""
                    
                    labels = fs.locator("label").all()
                    valid_labels = []
                    option_texts = []
                    for lbl in labels:
                        if lbl.is_visible():
                            txt = lbl.inner_text().strip()
                            if txt:
                                option_texts.append(txt)
                                valid_labels.append(lbl)
                                
                    if option_texts:
                        response = intent_engine.resolve_intent(
                            question_text=q_context, 
                            field_type="options", 
                            options=option_texts, 
                            profile=config
                        )
                        best_match_text = response.get("answer")
                        
                        clicked = False
                        if best_match_text:
                            for lbl in valid_labels:
                                if lbl.inner_text().strip() == best_match_text:
                                    lbl.scroll_into_view_if_needed(timeout=1000)
                                    lbl.click(timeout=2000)
                                    clicked = True
                                    break
                                    
                        if not clicked and valid_labels:
                            # Fallback: Just click the first radio
                            valid_labels[0].scroll_into_view_if_needed(timeout=1000)
                            valid_labels[0].click(timeout=2000)
                            
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

    max_applications = config.get("max_applications", 10)
    applied_count = 0

    for index, card in enumerate(job_cards):
        if applied_count >= max_applications:
            logger.info(f"Reached max applications limit ({max_applications}). Stopping.")
            break
            
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
            
            # ------------------------------------------------------------------
            # Apply Title Keywords Filter (if configured)
            # ------------------------------------------------------------------
            title_filter_keywords = config.get("title_filter_keywords", [])
            if title_filter_keywords:
                matched_title = False
                for keyword in title_filter_keywords:
                    if keyword.lower() in raw_title.lower():
                        matched_title = True
                        break
                
                if not matched_title:
                    logger.info(f" -> Title mismatch (does not contain: {title_filter_keywords}) — skipping.")
                    job_records.append({"title": job_title, "status": "Ignored", "reason": "Title mismatch"})
                    continue
            
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

                # Check for Easy Apply limit
                try:
                    limit_text = page.get_by_text("You reached today’s Easy Apply limit")
                    if limit_text.is_visible():
                        logger.warning(" -> Easy Apply limit reached! Stopping script.")
                        got_it_btn = page.get_by_role("button", name="Got it")
                        if not got_it_btn.is_visible():
                            got_it_btn = page.locator("button:has-text('Got it')")
                        if got_it_btn.is_visible():
                            got_it_btn.first.click(timeout=2000)
                            time.sleep(1)
                        job_records.append({"title": job_title, "status": "Failed", "reason": "Daily limit reached"})
                        return job_records
                except Exception as e:
                    logger.debug(f"Limit check error: {e}")

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
                        # Handle the small success popup cross sign (Dismiss) or Done button
                        try:
                            # Sometimes the dismiss button takes a moment to appear
                            dismiss_btn = page.locator("button[aria-label='Dismiss']").last
                            if dismiss_btn.is_visible(timeout=3000):
                                logger.info(" -> Closing post-submission popup (Dismiss)...")
                                dismiss_btn.click(timeout=2000)
                                time.sleep(1)
                            else:
                                # Fallback to looking for a 'Done' button if Dismiss is not found
                                done_btn = page.get_by_role("button", name="Done").last
                                if done_btn.is_visible(timeout=2000):
                                    logger.info(" -> Closing post-submission popup (Done)...")
                                    done_btn.click(timeout=2000)
                                    time.sleep(1)
                        except Exception as e:
                            logger.warning(f" -> Could not close post-submission popup: {e}")
                        job_records.append({"title": job_title, "status": "Applied", "reason": "Success"})
                        applied_count += 1
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
                job_records.append({"title": job_title, "status": "Ignored", "reason": "External apply / No Easy Apply btn", "link": page.url})

        except Exception as card_err:
            error_msg = str(card_err).lower()
            logger.error(f"Failed to process card index {index + 1}: {card_err}")
            job_records.append({"title": f"Job #{index + 1}", "status": "Failed", "reason": str(card_err)[:35]})
            
            # Handle out of memory / page crashes
            if "target closed" in error_msg or "out of memory" in error_msg or "crash" in error_msg or "disconnected" in error_msg:
                logger.critical("Critical browser error detected (e.g., Out of Memory). Stopping current page processing.")
                try:
                    # Attempt to refresh the page for safety, then break the loop
                    page.reload(wait_until="domcontentloaded", timeout=15000)
                    time.sleep(5)
                except:
                    pass
                break
                
            continue

    logger.info("Finished processing all job listings on this page")
    return job_records