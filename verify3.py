from playwright.sync_api import sync_playwright

def run_cuj(page):
    page.goto("http://localhost:3000/index.html")
    page.wait_for_timeout(1000)
    page.screenshot(path="verification4.png")

    # Try to find a card and click it
    cards = page.locator(".card")
    if cards.count() > 0:
        cards.first.click()
        page.wait_for_timeout(1000)
        page.screenshot(path="verification5.png")
    else:
        print("No cards found.")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(record_video_dir="/home/jules/verification/videos")
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
