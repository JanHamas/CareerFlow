from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()

    # Open first page
    page1 = context.new_page()
    page1.goto("https://example.com")
    print("Opened:", page1.url)

    # Open new tab
    page2 = context.new_page()
    page2.goto("https://google.com")
    print("Opened:", page2.url)

    # ---- Switch focus back to the first tab ----
    page1.bring_to_front()
    print("Switched back to:", page1.url)


    # ---- Now switch again to the second tab ----
    page2.bring_to_front()
    print("Switched again to:", page2.url)

    browser.close()
