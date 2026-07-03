from playwright.sync_api import Playwright, sync_playwright


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.linkedin.com/")
    page.get_by_role("link", name="Sign in", exact=True).click()
    page.get_by_role("textbox", name="Email or phone").click()
    page.get_by_role("textbox", name="Email or phone").click()
    page.get_by_role("textbox", name="Email or phone").fill("swapnildhamal7895@gmail.com")
    page.get_by_role("textbox", name="Password").click()
    page.get_by_role("textbox", name="Password").fill("Swapnil@7895")
    page.get_by_role("button", name="Sign in", exact=True).click()
    page.get_by_test_id("typeahead-input").click()
    page.get_by_test_id("typeahead-input").fill("python")
    page.get_by_test_id("typeahead-input").press("Enter")
    page.goto("https://www.linkedin.com/search/results/all/?keywords=python&origin=GLOBAL_SEARCH_HEADER")
    page.get_by_test_id("typeahead-input").click()
    page.get_by_test_id("typeahead-input").click()
    page.get_by_test_id("typeahead-results-overlay").click()
    page.get_by_role("radio", name="Filter by Jobs").click()
    page.get_by_role("radio", name="Filter by Easy Apply").click()
    page.get_by_role("button", name="Filter by Date posted").click()
    page.get_by_role("radio", name="Past week").click()
    page.get_by_role("link", name="Show results").click()
    page.get_by_role("button", name="Python Lead  (Verified job)").click()
    page.get_by_role("button", name="Python Developer RapidBrains").click()
    page.get_by_role("link", name="Easy Apply to this job").click()
    page.get_by_role("link", name="Easy Apply to this job").click()
    page.get_by_role("button", name="Continue to next step").click()
    page.get_by_role("button", name="Continue to next step").click()
    page.get_by_role("textbox", name="How many years of hands-on").click()
    page.get_by_role("textbox", name="How many years of hands-on").fill("4.6")
    page.get_by_role("textbox", name="How many years of hands-on").select_option("Yes")
    page.get_by_role("textbox", name="How immediate you can join?(").click()
    page.get_by_role("textbox", name="How immediate you can join?(").fill("60")
    page.get_by_role("button", name="Review your application").click()
    page.get_by_role("button", name="Submit application").click()
    page.get_by_role("button", name="Not now").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
