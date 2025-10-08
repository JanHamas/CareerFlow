import asyncio, random, re, os
from playwright_stealth import Stealth
from playwright.async_api import async_playwright
# from datetime import datetime
from config import config_input
# from utils.bypass.cloudflare import CloudflareBypasser
from utils import accounts_loader, fingerprint_loader, proxies_loader, helper
# from .scrapers.job_details_scraper import extract_full_details
import logging
from typing import List
                                                     

# get logger file for saving spider logs.
logger = logging.getLogger("spider")  # use shared logger


""" This function are submit application."""
async def submitter(easy_applies: List[List[str]]) -> None:

    accounts = await accounts_loader.load_accounts(config_input.INDEED_ACCOUNT_DIR)  # list of accounts

    async with Stealth().use_async(async_playwright()) as p:
        
        # create instance of browser with mode headed/headless
        browser = await p.chromium.launch(headless=config_input.headless)
 
        try:
            context = await browser.new_context()
            try:
                await context.add_cookies(accounts[len(accounts)])
            except:
                await context.add_cookies(random.choice(accounts))

            await _submiting_logic(context, easy_applies)

        except Exception as e:
            logger.exception(f"Context/Listing failed for {easy_applies}: {e}")


        await browser.close()

# Below are some methods with names of steps for submitting applications steps
async def step_1(context, page, url):
    # first scroll
    element_locator = page.locator("//span[normalize-space()='Continue']") 
    element_locator.scroll_into_view_if_needed()

    # Get page  context first
    content = await page.content()

    # Check if Applies is expired or already applied.
    if "<!-- -->This job has expired on Indeed<!-- -->" in content or 'aria-label="Applied "' in content:
        await content.page()
        if len(content.pages) > 0:
            # Get last page
            last_page = context.pages[-1]
            await last_page.bring_to_front()
            logger.info("Switched to last page")
        return
    
    # Check if CS Applies found.
    if "Apply now (opens in a new tab)" in content:
        await page.close()
        if len(context.pages) > 0:
            last_page = context.pages[-1]
            await last_page.bring_to_front()
            logger.info("CS Applies found.")
        return


async def _submiting_logic(context, easy_applies):
   
    # first create a new page_tab
    page = context.new_page()
    for job in easy_applies:
        url = job["url"]
        await page.evaluate(f"window.open('{url}', '_blank');") 
        
        # Switch to the new tab (last one opened) and Get last page
        last_page = context.pages[-1]
        await last_page.bring_to_front()
        logger.info("Switched to last page")

        # process step 1
        step1_result = step_1(context , url) 
        if step1_result is False:
            continue
        print("✅ Step 1 done.")
        
        # # process step 2
        # step2_result = step_2(url) 
        # if step2_result is False:
        #     continue
        # print("✅ Step 2 done.")

        # # process step 3
        # step3_result = step_3(url) 
        # if step3_result is False:
        #     continue
        # print("✅ Step 3 done.")
        
        # # process step 4
        # step4_result = step_3(url) 
        # if step4_result is False:
        #     continue
        # print("✅ Step 4 done.")

        # # process step 4
        # step5_result = step_3(url) 
        # if step5_result is False:
        #     continue
        # print("✅ Step 5 done.")

        # # process step 4
        # step6_result = step_3(url) 
        # if step6_result is False:
        #     continue
        # print("✅ Step 6 done.")

        # # process step 4
        # step7_result = step_3(url) 
        # if step7_result is False:
        #     continue
        # print("✅ Step 7 done.")

        # # process step 4
        # step8_result = step_3(url) 
        # if step8_result is False:
        #     continue
        # print("✅ Step 8 done.")



# Fake easy_applies data (same structure as the extractor output)
fake_easy_applies = [
    {
        "company_name": "Google",
        "url": "https://indeed.com/rc/clk?jk=44eaab9cf7af64e2&bb=UAg-HaDp2GSXsaSBv1Jhuf2ZRgoKsWckVHIfGJlCMSluD1P1tQ1Y2UbZO-mA_ZfLJurLq5PPY_nl5H63FR2JWpv3gxEQa4xus1nZtqn_9JsggyK5O86qdEaANP5AsNahfut5ED_T6AY%3D&xkcb=SoCr67M3sfIWbjTb0Z0ObzkdCdPP&fccid=8970a3ecb2f5b884&vjs=3",
        "matching_per": "95%",
        "job_title": "Software Engineer",
        "salary": "$120k",
        "job_other_details": "Full-time · Remote",
        "benefits": "Health, 401k, PTO",
        "full_description": "Build scalable systems and work with AI."
    },
    {
        "company_name": "Amazon",
        "url": "https://indeed.com/rc/clk?jk=814dedeac216c6ff&bb=UAg-HaDp2GSXsaSBv1JhuanitF9HI7PzwI2_o9jtAbJxUfYsPosTpq-CD1JYgeS6dMpAEUHDFNx66xx0YTPlN-XaEA9g2IUVGs8bG8l3tUZTNcPss6i50DKdS54UBgrtuh33gBKRcYs%3D&xkcb=SoBr67M3sfIWbjTb0Z0DbzkdCdPP&fccid=392469d55936230f&vjs=3",
        "matching_per": "88%",
        "job_title": "Backend Developer",
        "salary": "$110k",
        "job_other_details": "Hybrid · AWS team",
        "benefits": "Stock options, bonuses",
        "full_description": "Design microservices and cloud APIs."
    },
    {
        "company_name": "Netflix",
        "url": "https://indeed.com/rc/clk?jk=8de55859d5c1ddec&bb=UAg-HaDp2GSXsaSBv1JhuZhnTTz2iSDLiOhBtQsGtJuy-hT4o4RtvcHoAxRr5OTBih1GKz2cHYkYazeylJcLqdzOBb-srWAq38mc5dmIEn2UnX8k_Ao981kbsj6nOuK6T4r7sJO6kmg%3D&xkcb=SoAM67M3sfIWbjTb0Z0LbzkdCdPP&fccid=dd616958bd9ddc12&vjs=3",
        "matching_per": "92%",
        "job_title": "Frontend Engineer",
        "salary": "$130k",
        "job_other_details": "Full-time · React/TypeScript",
        "benefits": "Health, flexible hours",
        "full_description": "Work on the UI of streaming apps."
    }
]


# Run the submitter function to test
async def main():
    await submitter(easy_applies=fake_easy_applies)

asyncio.run(main())










