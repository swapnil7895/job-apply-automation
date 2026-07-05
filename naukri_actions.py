# naukri_actions.py
# Naukri automation — completely isolated from LinkedIn logic.
import time
import logging
import urllib.parse
import intent_engine

logger = logging.getLogger("NaukriAutomation")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def is_already_logged_in(page) -> tuple[bool, str]:
    """Checks if an active Naukri session exists.
    
    Checks URL first (fastest), then falls back to DOM element checks.
    Returns (True, user_name) if logged in, (False, "") otherwise.
    """
    logger.info("Checking Naukri authentication state...")
    user_name = ""
    try:
        time.sleep(4)
        current_url = page.url
        logger.info(f"Current URL: {current_url}")

        is_logged_in = False
        if any(x in current_url for x in [
            "mnjuser/homepage",
            "mnjuser/myapply",
            "naukri.com/my-jobs",
        ]):
            logger.info("Session active: logged-in URL detected.")
            is_logged_in = True

        if not is_logged_in:
            logged_in_locators = [
                page.locator("img[alt='naukri user profile img']"),
                page.locator(".nI-gNb-drawer__icon-img-wrapper"),
                page.locator(".nI-gNb-drawer"),
                page.locator("a[href*='mnjuser/homepage']"),
                page.locator("a[href*='mnjuser/profile']"),
                page.locator("a[title='Logout']"),
                page.locator("text='My Naukri'"),
                page.locator("text='View profile'"),
                page.locator("text='Edit profile'"),
                page.locator(".nI-gNb-usr__img"), # fallback to old class
            ]
            
            for loc in logged_in_locators:
                if loc.count() > 0:
                    logger.info(f"Session active: Logged-in element detected.")
                    is_logged_in = True
                    break

        if not is_logged_in:
            if page.locator("body").filter(has_text="My Naukri").count() > 0:
                logger.info("Session active: 'My Naukri' text found on page.")
                is_logged_in = True

        if is_logged_in:
            # Try to fetch user name
            try:
                name_locators = [
                    page.locator(".info__name"),
                    page.locator(".nI-gNb-info__sub-link"),
                    page.locator(".name"),
                    page.locator(".nI-gNb-drawer__name")
                ]
                for n_loc in name_locators:
                    if n_loc.count() > 0 and n_loc.first.is_visible(timeout=1000):
                        user_name = n_loc.first.inner_text().strip()
                        if user_name:
                            break
            except Exception as e:
                logger.warning(f"Failed to fetch user name: {e}")
            return True, user_name

        # Broad check for Login button
        login_btn = page.locator("a#login_Layer, text='Login', text='Log in'").filter(visible=True).first
        if login_btn.count() > 0:
            logger.info("Not logged in: Login button detected.")
            return False, ""

    except Exception as e:
        logger.debug(f"Auth check exception: {e}")

    logger.info("Could not confirm session. Treating as NOT logged in.")
    return False, ""

def logout(page) -> None:
    """Logs the user out by clearing cookies."""
    logger.info("Logging out from Naukri...")
    try:
        page.context.clear_cookies()
        page.goto("https://www.naukri.com/")
        time.sleep(2)
        logger.info("Logout successful.")
    except Exception as e:
        logger.error(f"Error during logout: {e}")


def login(page, username: str, password: str) -> None:
    """Handles routing to Naukri sign-in page and entering credentials.
    
    Mirrors LinkedIn's approach: navigate directly to the login URL,
    fill credentials, submit — and fall back to manual login if anything
    goes wrong (CAPTCHA, OTP, UI changes).
    """
    logger.info("Navigating to Naukri login page...")
    try:
        page.goto("https://www.naukri.com/nlogin/login")
        page.wait_for_load_state("domcontentloaded")
        time.sleep(3)

        # If already redirected to logged-in page, skip filling credentials
        if "mnjuser" in page.url:
            logger.info("Already redirected to logged-in page — skipping credentials.")
            return

        logger.info("Filling credentials...")

        # Fill email / username
        try:
            email_field = page.locator("input#usernameField")
            email_field.wait_for(state="visible", timeout=8000)
            email_field.fill(username)
        except Exception:
            email_field = page.locator(
                "input[type='email'], "
                "input[placeholder*='Email'], "
                "input[placeholder*='Username']"
            )
            email_field.first.fill(username)
        logger.info("Email entered.")

        # Fill password
        try:
            password_field = page.locator("input#passwordField")
            password_field.wait_for(state="visible", timeout=5000)
            password_field.fill(password)
        except Exception:
            password_field = page.locator("input[type='password']")
            password_field.first.fill(password)
        logger.info("Password entered.")

        # Submit
        try:
            submit_btn = page.locator("button[type='submit']")
            submit_btn.first.click()
        except Exception:
            page.locator("button").filter(has_text="Login").first.click()

        page.wait_for_load_state("domcontentloaded", timeout=15000)
        time.sleep(5)
        logger.info("Login submitted. Verifying session...")

        if not is_already_logged_in(page):
            logger.warning("Auto-login may have been blocked (OTP / CAPTCHA detected).")
            input("Please manually complete login in the browser, then press Enter here: ")

        logger.info("Successfully logged into Naukri!")

    except Exception as e:
        logger.warning(f"Login flow interrupted: {e}")
        input("Please manually complete login in the browser, then press Enter here: ")


# ---------------------------------------------------------------------------
# Job Search
# ---------------------------------------------------------------------------

def search_jobs(page, config: dict) -> None:
    """Handles keyword insertion and filter settings on Naukri job search."""
    keywords     = config.get("keywords", ["Python Developer"])
    if isinstance(keywords, list) and keywords:
        keywords = keywords[0]
    elif not isinstance(keywords, str):
        keywords = "Python Developer"
    
    location     = config.get("location", "Pune")
    experience   = config.get("experience", "5")
    company_type = config.get("company_type", "")
    apply_filter = config.get("easy_apply", True) # True = only show direct-apply jobs
    date_posted  = config.get("date_posted", "7")
    remote_only  = config.get("remote_only", False)

    logger.info(f"Searching Naukri jobs: '{keywords}' in '{location}'...")

    # Build search URL.
    # Use wait_until='commit' in goto — fires as soon as the navigation is
    # committed (URL changes). This prevents TargetClosedError that occurs
    # when Naukri's SPA rewrites the page context before domcontentloaded fires.
    search_url = (
        f"https://www.naukri.com/jobs-in-{urllib.parse.quote(location.lower())}"
        f"?k={urllib.parse.quote(keywords)}&l={urllib.parse.quote(location)}&experience={experience}"
    )
    logger.info(f"Navigating to: {search_url}")
    try:
        page.goto(search_url, wait_until="commit", timeout=20000)
    except Exception as e:
        logger.warning(f"goto() raised (non-fatal, continuing): {e}")
    time.sleep(7)  # Let Naukri's SPA fully render before touching anything
    logger.info(f"Search results page: {page.url}")

    # ----------------------------------------------------------------
    # Apply filters in order. Each wrapped individually so one failure
    # doesn't stop the rest.
    # ----------------------------------------------------------------

    # 1. 'Apply on Naukri' filter — shows only direct-apply jobs
    if apply_filter:
        _click_filter(page, [
            "label:has-text('Apply on Naukri')",
            "span:has-text('Apply on Naukri')",
            "input[value*='Apply on Naukri']",
        ], "'Apply on Naukri'")

    # 2. Company type filter (MNC / Indian MNC / Startup etc.)
    if company_type:
        _click_filter(page, [
            f"label:has-text('{company_type}')",
            f"span:has-text('{company_type}')",
            f"input[value='{company_type}']",
            f"a:has-text('{company_type}')",
        ], f"Company type '{company_type}'")

    # 3. Date Posted filter
    if date_posted == "1":
        _click_filter(page, ["label:has-text('Last 1 Day')", "span:has-text('Last 1 Day')"], "Date posted: Last 1 Day")
    elif date_posted == "7":
        _click_filter(page, ["label:has-text('Last 7 Days')", "span:has-text('Last 7 Days')"], "Date posted: Last 7 Days")
    elif date_posted == "30":
        _click_filter(page, ["label:has-text('Last 30 Days')", "span:has-text('Last 30 Days')"], "Date posted: Last 30 Days")

    # 4. Remote Filter
    if remote_only:
        _click_filter(page, ["label:has-text('Remote')", "span:has-text('Remote')"], "Remote Only")

    time.sleep(2)  # Let results refresh after filters
    logger.info(f"Filters applied. Final page: {page.url}")


def _click_filter(page, selectors: list, label: str) -> None:
    """Tries each selector in order and clicks the first visible match.
    Logs the outcome but never raises — filter failure is non-fatal.
    """
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.scroll_into_view_if_needed()
                el.click()
                time.sleep(2)
                logger.info(f"Filter applied: {label}")
                return
        except Exception:
            pass
    logger.info(f"Filter not found (skipping): {label}")



# ---------------------------------------------------------------------------
# Form Filling (right-side panel / chatbot on the job detail tab)
# ---------------------------------------------------------------------------

def fill_application_form(page, config: dict) -> None:
    """Detects and fills visible fields on a Naukri quick-apply panel."""
    # Find active panel/chatbot container to restrict search scope
    PANEL_CONTAINER_SELECTORS = [
        "div.chatbot_MessageContainer",
        "div.chatbot-popup",
        "div[class*='chatbot']",
        "div[class*='quick-apply']",
        "div[class*='applyForm']",
        "div[class*='apply-form']",
        "div[class*='apply-container']",
        "section[class*='apply']",
        "div[class*='questionnaire']",
        "div[class*='modal']",
    ]
    container = page
    for sel in PANEL_CONTAINER_SELECTORS:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=1000):
                container = el
                break
        except Exception:
            pass

    logger.info("   Scanning form fields...")

    # --- Chatbot contenteditable handling ---
    try:
        contenteditables = container.locator("div[contenteditable='true']").all()
        for el in contenteditables:
            if not el.is_visible():
                continue
            
            # Find the latest question text from the chat bubbles
            q_text = ""
            try:
                msgs = container.locator("div.botMsg, li.botItem, div.chipMsg, div[class*='Msg'], div.botMsg span").all()
                if msgs:
                    for m in reversed(msgs[-3:]):
                        txt = m.inner_text().strip()
                        if txt:
                            q_text = txt
                            break
            except Exception:
                pass
            
            combined = q_text.lower()
            is_yes_no = (
                any(kw in combined for kw in ["do you", "have you", "are you", "willing", "available", "ready", "relocat", "do u", "have u", "experience in"])
                and not any(kw in combined for kw in ["how many", "how much", "number of"])
            )

            # Let intent engine resolve it
            response = intent_engine.resolve_intent(combined, field_type="text", profile=config)
            answer = response.get("answer")
            
            # Additional fallback just in case intent engine fails and it's a yes/no
            if answer is None and is_yes_no:
                answer = "Yes"
            if not answer:
                answer = config.get("experience", "4")
            elif "mobile" in combined or "phone" in combined:
                answer = config.get("mobile", "")

            logger.info(f"   Chatbot question: '{q_text[:90]}'")
            logger.info(f"   Answering: '{answer}'")

            el.click(timeout=1500)
            time.sleep(0.2)
            el.press("Control+A")
            el.press("Backspace")
            time.sleep(0.1)
            el.type(answer)
            time.sleep(0.2)
            el.press("Enter")
            time.sleep(1.5)

            # Try to click send button if Enter didn't submit
            try:
                send_btn = container.locator("span[class*='send'], button[class*='send'], div[class*='send']").first
                if send_btn.is_visible(timeout=1000):
                    send_btn.click()
                    time.sleep(1.5)
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"   Chatbot handling error: {e}")

    # Helper function to type values safely
    def safe_type(el, val: str):
        try:
            el.click(timeout=1500)
            time.sleep(0.2)
            # Clear field
            el.press("Control+A")
            el.press("Backspace")
            time.sleep(0.1)
            el.fill(val, timeout=1500)
        except Exception:
            try:
                el.type(val, timeout=1500)
            except Exception:
                pass

    inputs = container.locator("input, textarea, select").all()
    for el in inputs:
        try:
            if not el.is_visible():
                continue

            tag = el.evaluate("el => el.tagName").lower()

            if tag == "select":
                try:
                    el.select_option(label="Yes", timeout=2000)
                except Exception:
                    options = el.locator("option").all()
                    if len(options) > 1:
                        val = options[1].get_attribute("value")
                        if val:
                            el.select_option(val, timeout=2000)

            elif tag in ["input", "textarea"]:
                input_type = (el.get_attribute("type") or "").lower()
                if input_type in ["radio", "checkbox", "hidden", "submit", "button", "file"]:
                    continue

                if el.is_editable():
                    # Even if there's a default/placeholder, we might want to check it.
                    # But let's check the labels and preceding texts.
                    el.scroll_into_view_if_needed(timeout=1000)

                    name_attr   = el.get_attribute("name")        or ""
                    id_attr     = el.get_attribute("id")          or ""
                    placeholder = el.get_attribute("placeholder") or ""
                    aria_label  = el.get_attribute("aria-label")  or ""
                    
                    # Robust label text extraction (avoiding parentElement.parentElement which grabs the whole form)
                    label_text  = el.evaluate(
                        "el => { "
                        "  let text = ''; "
                        "  const l = document.querySelector(`label[for='${el.id}']`); "
                        "  if (l) text += l.innerText + ' '; "
                        "  let p = el.parentElement; "
                        "  if (p) text += p.innerText + ' '; "
                        "  let prev = el.previousElementSibling; "
                        "  while (prev) { text += prev.innerText + ' '; prev = prev.previousElementSibling; } "
                        "  return text; "
                        "}"
                    )
                    combined = (name_attr + id_attr + placeholder + aria_label + label_text).lower()

                    is_yes_no = (
                        any(kw in combined for kw in ["do you", "have you", "are you", "willing", "available", "ready", "relocat", "do u", "have u", "experience in"])
                        and not any(kw in combined for kw in ["how many", "how much", "number of"])
                    )

                    response = intent_engine.resolve_intent(combined, field_type="text", profile=config)
                    answer = response.get("answer")
                    
                    if answer is None and is_yes_no:
                        answer = "Yes"
                    if not answer:
                        answer = config.get("experience", "4")
                    
                    safe_type(el, answer)
                    
                    # Special handling for autocomplete location drop downs if location intent was resolved
                    if response.get("field") == "location" and any(kw in combined for kw in ["location", "city"]):
                        time.sleep(1)
                        el.press("ArrowDown")
                        time.sleep(0.5)
                        el.press("Enter")

        except Exception as e:
            logger.debug(f"   Form fill error: {e}")

    # ----------------------------------------------------------------
    # Handle radio buttons — Naukri has THREE styles:
    #
    # Style A (traditional HTML): fieldset > input[type=radio] + label
    # Style B (Naukri chatbot modal option chips): clickable spans / divs / chips
    # Style C (Chatbot Custom Radio inputs): div.singleselect-radiobutton + labels
    # ----------------------------------------------------------------

    # Style A — fieldsets with real radio inputs
    fieldsets = container.locator("fieldset").all()
    for fs in fieldsets:
        try:
            if not fs.is_visible():
                continue
            if fs.locator("input[type='radio']:checked").count() == 0:
                yes_label = fs.locator("label").filter(has_text="Yes")
                if yes_label.count() > 0 and yes_label.first.is_visible():
                    yes_label.first.click(timeout=2000)
                else:
                    first_label = fs.locator("label").first
                    if first_label.is_visible():
                        first_label.click(timeout=2000)
                time.sleep(0.3)
        except Exception as e:
            logger.debug(f"   [FieldsetRadio] error: {e}")

    # Style C & B — Chatbot Custom Radio inputs / chips / checkboxes
    # This matches the "singleselect-radiobutton-container" and other custom container classes
    CHATBOT_OPTION_CONTAINERS = [
        "div[class*='singleselect-radiobutton']",
        "div[class*='radiobutton']",
        "div[class*='multiselect']",
        "div[class*='checkbox']",
        "div[class*='multi-select']",
        "ul[class*='dropdown-list']",
        "div[class*='option-list']",
        "div[class*='answer-options']",
        "div[class*='radio-group']",
        "div[class*='chatbot'] div[class*='row']",
        "div.options-container",
        "div[class*='options']",
    ]
    for container_sel in CHATBOT_OPTION_CONTAINERS:
        containers = container.locator(container_sel).all()
        for cont in containers:
            try:
                if not cont.is_visible():
                    continue

                # Check if any radio/option is already selected in this group
                already_answered = cont.evaluate(
                    "el => {"
                    "  const checked = el.querySelector('input:checked, [class*=\"selected\"], [class*=\"active\"], [aria-checked=\"true\"]');"
                    "  return !!checked;"
                    "}"
                )
                if already_answered:
                    continue  # already answered this group


                # Get context text of the latest question asked by the chatbot
                q_context = ""
                try:
                    bot_msgs = container.locator("div.botMsg, li.botItem, div.chipMsg, div[class*='botMsg']").all()
                    if bot_msgs:
                        q_context = bot_msgs[-1].inner_text().strip().lower()
                except Exception:
                    pass

                if not q_context:
                    q_context = cont.evaluate(
                        "el => el.parentElement ? el.parentElement.innerText : el.innerText"
                    ).lower()

                # Find clickable option elements (labels, buttons, spans, inputs/checkboxes)
                options = cont.locator(
                    "label, span, li, button, input[type='radio'], input[type='checkbox']"
                ).all()
                clicked = False

                # Extract visible text of all options
                option_texts = []
                valid_opts = []
                for opt in options:
                    try:
                        if opt.is_visible():
                            txt = opt.inner_text().strip()
                            if txt:
                                option_texts.append(txt)
                                valid_opts.append(opt)
                    except Exception:
                        pass
                
                if option_texts:
                    # Let the intent engine pick the best option
                    response = intent_engine.resolve_intent(
                        question_text=q_context, 
                        field_type="options", 
                        options=option_texts, 
                        profile=config
                    )
                    best_match_text = response.get("answer")
                    
                    if best_match_text:
                        for opt in valid_opts:
                            try:
                                if opt.inner_text().strip() == best_match_text:
                                    opt.click(timeout=1500)
                                    time.sleep(0.3)
                                    clicked = True
                                    logger.info(f"   Resolved intent option: {best_match_text}")
                                    break
                            except Exception:
                                pass
                                
                # Fallback to the first visible option if intent engine couldn't click anything
                if not clicked and valid_opts:
                    try:
                        valid_opts[0].click(timeout=1500)
                        time.sleep(0.3)
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"   [ChatbotRadio] error: {e}")



def _handle_quick_apply_panel(job_page, config: dict) -> bool:
    """Called after clicking Apply on a Naukri job detail tab.

    Naukri has 3 apply types after you click Apply:

    Type 1 — Immediate apply:
        No panel opens. The page immediately shows an 'Applied' confirmation
        (e.g., a green tick, 'Applied to <company>' text). Nothing more to do.

    Type 2 — Questionnaire panel (right-side modal/chatbot):
        A panel slides in on the right. We fill questions and submit.

    Type 3 — Nothing (handled before calling this function):
        Company-site jobs are filtered out before we click Apply,
        so they never reach here.

    Returns True  → application confirmed (either immediate or via panel).
    Returns False → could not confirm — tab will be closed and job skipped.
    """
    time.sleep(3)  # Give the page a moment to react after clicking Apply

    # ----------------------------------------------------------------
    # Check Type 1 — Immediate apply confirmation
    # Naukri shows text like 'Applied to Acme Corp' or 'Your application
    # has been submitted' or a green 'Applied' badge.
    # ----------------------------------------------------------------
    APPLIED_CONFIRMATION_SELECTORS = [
        "text='applied successfully'",
        "text='successfully applied'",
        "text='application has been submitted'",
        "text='application submitted'",
        "text='Applied to '",
        "text='Applied successfully'",
        "div.applied-message",
        "div.success-message",
        "div.confirmation",
        ".apply-message",
        ".success-msg"
    ]
    for sel in APPLIED_CONFIRMATION_SELECTORS:
        try:
            el = job_page.locator(sel).first
            if el.is_visible(timeout=1500):
                logger.info(f"   Type 1 (Immediate apply): confirmation visible via '{sel}'.")
                return True
        except Exception:
            pass

    # ----------------------------------------------------------------
    # Check Type 2 — Right-side questionnaire panel
    # ----------------------------------------------------------------
    PANEL_SELECTORS = [
        "div.chatbot-popup",
        "div[class*='chatbot']",
        "div[class*='quick-apply']",
        "div[class*='applyForm']",
        "div[class*='apply-form']",
        "div[class*='apply-container']",
        "section[class*='apply']",
        "div[class*='questionnaire']",
        "div[class*='modal']:has(button:has-text('Next'))",
        "div[class*='modal']:has(button:has-text('Submit'))",
    ]
    panel_found = False
    for sel in PANEL_SELECTORS:
        try:
            el = job_page.locator(sel).first
            if el.is_visible(timeout=2000):
                panel_found = True
                logger.info(f"   Type 2 (Questionnaire panel): found via '{sel}'.")
                break
        except Exception:
            pass

    if not panel_found:
        logger.info("   No confirmation or panel detected — could not confirm application.")
        return False

    # Multi-step questionnaire form navigation
    max_steps = 15
    for step in range(max_steps):
        # 1. At each step, check if the job is already applied/submitted successfully
        for sel in APPLIED_CONFIRMATION_SELECTORS:
            try:
                el = job_page.locator(sel).first
                if el.is_visible(timeout=1000):
                    logger.info(f"   Application confirmation detected in loop step {step + 1} via '{sel}'.")
                    return True
            except Exception:
                pass

        # 2. Fill the form/chatbot input
        fill_application_form(job_page, config)
        time.sleep(1)

        # 3. Check for buttons and chatbot state
        next_btn = job_page.locator("button:has-text('Next'), button:has-text('Continue')").first
        submit_btn = job_page.locator(
            "button:has-text('Submit'), "
            "button[type='submit']:not([style*='display: none']), "
            "div.sendMsg, "
            "div[class*='sendMsg'], "
            "div[id^='sendMsg']"
        ).first
        
        # Determine if chatbot is active: either the text input is visible OR custom options/radios are visible
        chatbot_input = job_page.locator("div[contenteditable='true']").first
        has_text_input = chatbot_input.is_visible() if chatbot_input.count() > 0 else False

        has_chatbot_options = False
        for opt_sel in ["div[class*='singleselect']", "div[class*='multiselect']", "div[class*='checkbox']", "div.singleselect-radiobutton-container"]:
            try:
                if job_page.locator(opt_sel).first.is_visible(timeout=300):
                    has_chatbot_options = True
                    break
            except Exception:
                pass

        is_chatbot_active = has_text_input or has_chatbot_options

        if submit_btn.is_visible():
            # If it's a custom chatbot sendMsg button, check if it's currently disabled.
            # If so, wait for it to become enabled (up to 3 seconds).
            btn_html = submit_btn.evaluate("el => el.outerHTML").lower()
            is_chatbot_arrow = "sendmsg" in btn_html
            
            if is_chatbot_arrow and has_text_input:
                logger.info("   Detected 'sendMsg' arrow for a text input. Continuing chatbot loop...")
                time.sleep(2)
                continue

            try:
                classes = submit_btn.get_attribute("class") or ""
                if "disabled" in classes:
                    logger.info("   Submit button is currently disabled. Waiting for activation...")
                    for _ in range(6):
                        time.sleep(0.5)
                        if "disabled" not in (submit_btn.get_attribute("class") or ""):
                            break
            except Exception:
                pass

            try:
                submit_btn.scroll_into_view_if_needed()
            except Exception:
                pass
            logger.info("   Submitting questionnaire...")
            time.sleep(1)
            submit_btn.click()
            time.sleep(3)

            # Dismiss any post-submit popup
            try:
                close_btn = job_page.locator(
                    "button[aria-label='Close'], span.crossIcon, "
                    "button:has-text('Close'), button:has-text('Done')"
                ).first
                if close_btn.is_visible(timeout=2000):
                    close_btn.click()
                    time.sleep(1)
            except Exception:
                pass

            logger.info("   Application submitted successfully!")
            return True

        elif next_btn.is_visible():
            try:
                next_btn.scroll_into_view_if_needed()
            except Exception:
                pass
            next_btn.click()
            time.sleep(2)

        elif is_chatbot_active:
            # Chatbot is still waiting for input/answering next questions
            logger.info(f"   Chatbot step {step + 1} completed. Waiting for chatbot's response...")
            time.sleep(3)
            continue

        else:
            # Double check confirmation before declaring failure
            for sel in APPLIED_CONFIRMATION_SELECTORS:
                try:
                    el = job_page.locator(sel).first
                    if el.is_visible(timeout=1000):
                        logger.info("   Application confirmation visible at end of flow.")
                        return True
                except Exception:
                    pass
            logger.warning("   Stuck — cannot find Next, Submit, or active chatbot. Aborting.")
            break

    return False


# ---------------------------------------------------------------------------
# Main Application Loop
# ---------------------------------------------------------------------------

def apply_to_jobs(page, config: dict) -> list:
    """Iterates job cards on Naukri search results and applies to each one.
    Returns a list of job processing records.
    
    Naukri's actual apply flow:
    1. Search results page shows job cards — there is NO Apply button on the card.
    2. Click the job title link → a NEW TAB opens with the full job detail page.
    3. On that new tab, find and click the 'Apply' button.
    4. Clicking Apply opens a right-side quick-apply panel / chatbot.
    5. If panel appears  → fill form → submit → close tab → back to search tab.
    6. If no panel       → external/redirect apply, skip → close tab → back to search tab.
    """
    logger.info("Starting Naukri Job Application Loop...")
    job_records = []

    context = page.context
    search_tab = page  # Keep a firm reference to the search results tab

    # Naukri job card selectors (try multiple — DOM changes frequently)
    CARD_SELECTORS = [
        "div.srp-jobtuple-wrapper",
        "article.jobTuple",
        "div[data-job-id]",
        ".job-card-container",
    ]

    job_card_selector = None
    for sel in CARD_SELECTORS:
        try:
            page.locator(sel).first.wait_for(state="visible", timeout=5000)
            count = page.locator(sel).count()
            if count > 0:
                job_card_selector = sel
                logger.info(f"Using job card selector: '{sel}' ({count} cards)")
                break
        except Exception:
            pass

    if not job_card_selector:
        logger.error("No Naukri job cards found on the page. Aborting.")
        return job_records

    # Scroll to lazy-load all cards then back to top.
    # Use mouse.wheel (browser-level input) not page.evaluate/JS —
    # evaluate crashes if Naukri triggers a background navigation mid-scroll.
    logger.info("Scrolling to load all job listings...")
    for _ in range(4):
        try:
            page.mouse.wheel(0, 800)
        except Exception:
            pass
        time.sleep(1.5)
    try:
        page.mouse.wheel(0, -9999)  # scroll back to top
    except Exception:
        pass
    time.sleep(2)

    job_cards = page.locator(job_card_selector).all()
    total = len(job_cards)
    logger.info(f"Found {total} job cards.")

    max_applications = config.get("max_applications", 10)
    applied_count = 0

    for index, card in enumerate(job_cards):
        if applied_count >= max_applications:
            logger.info(f"Reached max applications limit ({max_applications}). Stopping.")
            break

        job_page = None
        break_loop = False
        try:
            # ------------------------------------------------------------------
            # Extract job title for logging
            # ------------------------------------------------------------------
            title_el = card.locator(
                "a.title, a.jobTitle, h2 a, .title a, a[title]"
            ).first
            
            comp_el = card.locator(
                "a.comp-name, a.company, .companyName, .m-name a"
            ).first
            
            raw_title = title_el.inner_text().strip() if title_el.count() > 0 and title_el.is_visible() else f"Job #{index + 1}"
            raw_comp = comp_el.inner_text().strip() if comp_el.count() > 0 and comp_el.is_visible() else "Unknown Company"
            
            job_title = f"{raw_title} at {raw_comp}"
            logger.info(f"[{index + 1}/{total}] Processing: {job_title}")

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

            card.scroll_into_view_if_needed()
            time.sleep(0.5)

            # Skip if already applied badge visible on card
            already_applied = card.locator(
                "span:has-text('Applied'), button:has-text('Applied'), "
                "div:has-text('Applied on')"
            )
            if already_applied.count() > 0 and already_applied.first.is_visible():
                logger.info(" -> Already applied — skipping.")
                job_records.append({"title": job_title, "status": "Ignored", "reason": "Already applied"})
                continue

            # ------------------------------------------------------------------
            # Click the job title → Naukri opens the job detail in a NEW TAB
            # ------------------------------------------------------------------
            if title_el.count() == 0 or not title_el.is_visible():
                logger.info(" -> Could not find clickable title — skipping.")
                job_records.append({"title": job_title, "status": "Failed", "reason": "Could not find clickable title"})
                continue

            logger.info(" -> Clicking job title (new tab expected)...")
            try:
                with context.expect_page(timeout=8000) as new_page_info:
                    title_el.click()
                job_page = new_page_info.value
            except Exception:
                logger.info(" -> No new tab detected — skipping.")
                job_records.append({"title": job_title, "status": "Failed", "reason": "No new tab detected"})
                _close_extra_tabs(context, search_tab)
                search_tab.bring_to_front()
                continue

            job_page.wait_for_load_state("domcontentloaded", timeout=15000)
            # Let Naukri's SPA finish rendering the job detail page
            time.sleep(3)
            try:
                job_page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            time.sleep(1)
            logger.info(f" -> Job detail tab: {job_page.url}")

            # ------------------------------------------------------------------
            # On the job detail tab — classify the Apply button type first.
            #
            # Naukri shows 3 button types:
            #   1. "Apply"  /  "Apply on Naukri"  — direct apply (we want these)
            #   2. "Apply on Company Site"         — external redirect, SKIP
            #   3. "Interested" / walk-in jobs     — handled like apply
            # ------------------------------------------------------------------

            # Scroll to top so sticky header buttons are in view
            try:
                job_page.mouse.wheel(0, -5000)  # scroll to top
                time.sleep(1)
            except Exception:
                pass

            # --- Check for "Apply on Company Site" FIRST and skip immediately ---
            COMPANY_SITE_TEXTS = [
                "Apply on Company Site",
                "Apply on company's site",
                "Apply on company site",
                "company-site-button",
            ]
            is_company_site_job = False
            for cst in COMPANY_SITE_TEXTS:
                try:
                    # Match by text OR by id
                    el = job_page.locator(
                        f"button:has-text('{cst}'), a:has-text('{cst}'), button#{cst}"
                    ).first
                    if el.is_visible(timeout=1500):
                        is_company_site_job = True
                        logger.info(f" -> SKIP: 'Apply on Company Site' button detected — external apply job.")
                        break
                except Exception:
                    pass

            if is_company_site_job:
                job_records.append({"title": job_title, "status": "Ignored", "reason": "Apply on Company Site", "link": job_page.url})
                job_page.close()
                search_tab.bring_to_front()
                time.sleep(1)
                continue

            # --- Now look for a real direct-apply button ---
            # Known selectors in priority order (ID-based are most stable)
            APPLY_BTN_SELECTORS = [
                "#apply-button",                       # Naukri's stable ID for direct apply
                "#walkin-button",                      # Walk-in / Interested jobs
                "button:has-text('Apply on Naukri')",
                "a:has-text('Apply on Naukri')",
                "button:has-text('Apply')",
                "a:has-text('Apply')",
                "button:has-text('Interested')",
                "button[class*='apply']",
                "div.apply-button button",
                "div[class*='apply-btn'] button",
                "div[class*='applyBtn'] button",
                "div[class*='jd-header'] button",
                "div[class*='jdHeader'] button",
            ]

            apply_btn = None
            for btn_sel in APPLY_BTN_SELECTORS:
                try:
                    el = job_page.locator(btn_sel).first
                    if el.is_visible(timeout=2000):
                        apply_btn = el
                        logger.info(f" -> Apply button found via: '{btn_sel}'")
                        break
                except Exception:
                    pass

            if apply_btn is None:
                # Debug: log all visible button texts to identify the right selector
                try:
                    all_btns = job_page.locator("button, a[role='button']").all()
                    btn_texts = []
                    for b in all_btns[:15]:
                        try:
                            t = b.inner_text().strip()
                            if t:
                                btn_texts.append(repr(t))
                        except Exception:
                            pass
                    logger.info(f" -> Buttons on page: {btn_texts}")
                except Exception:
                    pass
                logger.info(" -> No Apply button found — closing tab.")
                job_records.append({"title": job_title, "status": "Failed", "reason": "No Apply button found"})
                job_page.close()
                search_tab.bring_to_front()
                time.sleep(1)
                continue

            logger.info(" -> Clicking Apply on job detail tab...")
            apply_btn.scroll_into_view_if_needed()
            apply_btn.click()
            time.sleep(3)

            # ------------------------------------------------------------------
            # Handle the right-side quick-apply panel
            # ------------------------------------------------------------------
            applied = _handle_quick_apply_panel(job_page, config)

            if applied:
                logger.info(" -> Done! Closing job tab.")
                job_records.append({"title": job_title, "status": "Applied", "reason": "Success"})
                applied_count += 1
            else:
                logger.info(" -> External apply — closing tab.")
                job_records.append({"title": job_title, "status": "Ignored", "reason": "External apply / Form failed", "link": job_page.url})

        except Exception as e:
            logger.error(f"Error on card {index + 1}: {e}")
            job_records.append({"title": job_title if 'job_title' in locals() else f"Job #{index+1}", "status": "Failed", "reason": str(e)[:35]})

        finally:
            # Always close the job detail tab and return to the search tab.
            # search_tab.bring_to_front() can crash if Naukri replaced the page,
            # so we do a safe recovery: try bring_to_front, fall back to any page.
            if job_page is not None:
                try:
                    job_page.close()
                except Exception:
                    pass
            _close_extra_tabs(context, search_tab)
            try:
                search_tab.bring_to_front()
            except Exception:
                # search_tab is gone — recover: use whatever page is still alive
                surviving = context.pages
                if surviving:
                    search_tab = surviving[0]  # reassign so next iteration works
                    try:
                        search_tab.bring_to_front()
                    except Exception:
                        pass
                else:
                    logger.error("All browser tabs closed — cannot continue.")
                    break_loop = True
            time.sleep(1)

        if break_loop:
            break

    logger.info("Finished processing all Naukri job listings.")
    return job_records


def _close_extra_tabs(context, keep_page) -> None:
    """Closes all browser tabs except the search results tab."""
    for p in context.pages:
        if p != keep_page:
            try:
                p.close()
            except Exception:
                pass
