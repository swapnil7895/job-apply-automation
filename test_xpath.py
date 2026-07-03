from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=r"C:\Users\swapn\ChromeAutomationProfile",
            channel="chrome",
            headless=True,
            no_viewport=True,
            args=[
                "--disable-extensions",
                "--disable-gpu"
            ]
        )
        page = context.pages[0]
        page.goto("https://www.linkedin.com/jobs/search/?keywords=Python&location=United%20States")
        page.wait_for_load_state("domcontentloaded")
        
        try:
            page.wait_for_selector(".job-card-container", timeout=15000)
        except:
            pass
        
        time.sleep(5) # let it load
        
        print("Count of .job-card-container:", page.locator(".job-card-container").count())
        
        xpath = "xpath=//*[@componentkey='SearchResultsMainContent']//div[contains(@data-display-contents, 'true')]/div[contains(@componentkey, 'job-card-component-ref')]"
        print("Count of custom xpath:", page.locator(xpath).count())
        
        print("Count of jobs-search-results__list-item:", page.locator("li.jobs-search-results__list-item").count())
        
        print("Count of div[data-job-id]:", page.locator("div[data-job-id]").count())
        
        # also scroll down the left pane and check again
        pane = page.locator('.jobs-search-results-list')
        if pane.is_visible():
            pane.evaluate("el => el.scrollTo(0, el.scrollHeight)")
            time.sleep(3)
            print("After scrolling:")
            print("Count of custom xpath:", page.locator(xpath).count())
            print("Count of .job-card-container:", page.locator(".job-card-container").count())
            
        context.close()

if __name__ == "__main__":
    run()
