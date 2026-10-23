from playwright.sync_api import sync_playwright
import json

# Let's mock the initial catalog so we can see some data
mock_data = [
    {
        "t": "Inception",
        "y": 2010,
        "o": ["Netflix", "Prime Video", "JioHotstar", "SonyLIV", "JioCinema", "HBO Max"],
        "poster": "",
        "g": ["Sci-Fi", "Action"]
    }
]

with open('data/catalog.json', 'w') as f:
    json.dump(mock_data, f)

def run_cuj(page):
    page.goto("file:///app/index.html")
    page.wait_for_timeout(1000)
    page.screenshot(path="verification2.png")

    # Click on the first card
    page.click(".card")
    page.wait_for_timeout(1000)
    page.screenshot(path="verification3.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
