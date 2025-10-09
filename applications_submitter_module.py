import asyncio, random, re, os, sys
from playwright_stealth import Stealth
from playwright.async_api import async_playwright
# from datetime import datetime
from config import config_input
# from utils.bypass.cloudflare import CloudflareBypasser
from utils import accounts_loader, fingerprint_loader, proxies_loader, helper
# from .scrapers.job_details_scraper import extract_full_details
import logging
from typing import List
from utils.logger_setup import setup_logger
import aioconsole
from datetime import datetime
# await aioconsole.ainput("Press enter")                                                     

# get logger file for saving spider logs.
logger = logging.getLogger("spider")  # use shared logger

async def step_1(context, page, url):
    ''' This function are just confirm some conditions for jobs before further submittions process. '''

    # get content of page
    content = await page.content()

    # check if job expired or already applied
    if "This job has expiredd" in content or 'aria-label="Applied "' in content:
        pages = context.pages
        if len(pages) > 0:
            last_page = pages[-1]
            await last_page.bring_to_front()
            logger.info("Jobs are expired or Applied")
        return False
    
    # If "Apply now" opens in new tab
    if "Apply now (opens in a new tab)" in content:
        await page.close()
        pages = context.pages
        if len(pages) > 0:
            last_page = pages[-1]
            await last_page.bring_to_front()
        logger.info("Jobs are CS Apply.")
        return False

    return True

async def step_2(context, page, url):
   ''' This one function will be only click buttons for nevigating to question pages'''
   # Click on Apply now button
   try:
       await page.get_by_text("Apply now").click()
       logger.info("Successfuly Click on Apply now button.")
   except Exception as e:
       logger.info("Failed to click on first continue button.")
       return False
   
   # Click first continue button
   try:
        # Wait for the "Continue" button or iframe to appear
        await asyncio.sleep(3)  # small delay after Apply Now
        logger.info("⏳ Searching for 'Continue' button...")

        # 1️⃣ Check if any iframe contains the continue button
        found = False
        for frame in page.frames:
            if "indeedapply" in frame.url or "apply" in frame.url:
                logger.info(f"🔍 Found iframe: {frame.url}")
                buttons = frame.locator("button:has-text('Continue')")
                count = await buttons.count()
                logger.info(f"Found {count} Continue buttons inside iframe.")
                for i in range(count):
                    btn = buttons.nth(i)
                    if await btn.is_visible():
                        await btn.click()
                        logger.info(f"✅ Clicked 'Continue' inside iframe (#{i}).")
                        found = True
                        break
                if found:
                    break

        # 2️⃣ If not found inside iframe, try on main page
        if not found:
            await page.wait_for_selector("button:has-text('Continue')", timeout=20000)
            buttons = page.locator("button:has-text('Continue')")
            count = await buttons.count()
            logger.info(f"Found {count} Continue buttons on main page.")
            for i in range(count):
                btn = buttons.nth(i)
                if await btn.is_visible():
                    await btn.click()
                    logger.info(f"✅ Clicked 'Continue' button on main page (#{i}).")
                    found = True
                    break

        if not found:
            logger.warning("❌ No visible or clickable 'Continue' button found.")
            return False

        await asyncio.sleep(5)
   except Exception as e:
        logger.warning(f"❌ Failed to click on first'Continue' button: {e}")
        return False

   # Click second continue button 
   if "contact-info-module" in page.url:
    try:
            # Wait for the "Continue" button or iframe to appear
            await asyncio.sleep(3)  # small delay after Apply Now
            logger.info("⏳ Searching for 'Continue' button...")

            # 1️⃣ Check if any iframe contains the continue button
            found = False
            for frame in page.frames:
                if "indeedapply" in frame.url or "apply" in frame.url:
                    logger.info(f"🔍 Found iframe: {frame.url}")
                    buttons = frame.locator("button:has-text('Continue')")
                    count = await buttons.count()
                    logger.info(f"Found {count} Continue buttons inside iframe.")
                    for i in range(count):
                        btn = buttons.nth(i)
                        if await btn.is_visible():
                            await btn.click()
                            logger.info(f"✅ Clicked 'Continue' inside iframe (#{i}).")
                            found = True
                            break
                    if found:
                        break

            # 2️⃣ If not found inside iframe, try on main page
            if not found:
                await page.wait_for_selector("button:has-text('Continue')", timeout=20000)
                buttons = page.locator("button:has-text('Continue')")
                count = await buttons.count()
                logger.info(f"Found {count} Continue buttons on main page.")
                for i in range(count):
                    btn = buttons.nth(i)
                    if await btn.is_visible():
                        await btn.click()
                        logger.info(f"✅ Clicked 'Continue' button on main page (#{i}).")
                        found = True
                        break

            if not found:
                logger.warning("❌ No visible or clickable 'Continue' button found.")
                return False

            await asyncio.sleep(5)
    except Exception as e:
            logger.warning(f"❌ Failed to click on second'Continue' button: {e}")
            return False
   
   # Click second continue button 
   if "profile-location" in page.url:
    try:
            # Wait for the "Continue" button or iframe to appear
            await asyncio.sleep(3)  # small delay after Apply Now
            logger.info("⏳ Searching for 'Continue' button...")

            # 1️⃣ Check if any iframe contains the continue button
            found = False
            for frame in page.frames:
                if "indeedapply" in frame.url or "apply" in frame.url:
                    logger.info(f"🔍 Found iframe: {frame.url}")
                    buttons = frame.locator("button:has-text('Continue')")
                    count = await buttons.count()
                    logger.info(f"Found {count} Continue buttons inside iframe.")
                    for i in range(count):
                        btn = buttons.nth(i)
                        if await btn.is_visible():
                            await btn.click()
                            logger.info(f"✅ Clicked 'Continue' inside iframe (#{i}).")
                            found = True
                            break
                    if found:
                        break

            # 2️⃣ If not found inside iframe, try on main page
            if not found:
                await page.wait_for_selector("button:has-text('Continue')", timeout=20000)
                buttons = page.locator("button:has-text('Continue')")
                count = await buttons.count()
                logger.info(f"Found {count} Continue buttons on main page.")
                for i in range(count):
                    btn = buttons.nth(i)
                    if await btn.is_visible():
                        await btn.click()
                        logger.info(f"✅ Clicked 'Continue' button on main page (#{i}).")
                        found = True
                        break

            if not found:
                logger.warning("❌ No visible or clickable 'Continue' button found.")
                return False

            await asyncio.sleep(5)
    except Exception as e:
            logger.warning(f"❌ Failed to click on second'Continue' button: {e}")
            return False
   
   # Click second continue button 
   if "resume" in page.url:
    try:
            # Wait for the "Continue" button or iframe to appear
            await asyncio.sleep(3)  # small delay after Apply Now
            logger.info("⏳ Searching for 'Continue' button...")

            # 1️⃣ Check if any iframe contains the continue button
            found = False
            for frame in page.frames:
                if "indeedapply" in frame.url or "apply" in frame.url:
                    logger.info(f"🔍 Found iframe: {frame.url}")
                    buttons = frame.locator("button:has-text('Continue')")
                    count = await buttons.count()
                    logger.info(f"Found {count} Continue buttons inside iframe.")
                    for i in range(count):
                        btn = buttons.nth(i)
                        if await btn.is_visible():
                            await btn.click()
                            logger.info(f"✅ Clicked 'Continue' inside iframe (#{i}).")
                            found = True
                            break
                    if found:
                        break

            # 2️⃣ If not found inside iframe, try on main page
            if not found:
                await page.wait_for_selector("button:has-text('Continue')", timeout=20000)
                buttons = page.locator("button:has-text('Continue')")
                count = await buttons.count()
                logger.info(f"Found {count} Continue buttons on main page.")
                for i in range(count):
                    btn = buttons.nth(i)
                    if await btn.is_visible():
                        await btn.click()
                        logger.info(f"✅ Clicked 'Continue' button on main page (#{i}).")
                        found = True
                        break

            if not found:
                logger.warning("❌ No visible or clickable 'Continue' button found.")
                return False

            await asyncio.sleep(5)
    except Exception as e:
            logger.warning(f"❌ Failed to click on second'Continue' button: {e}")
            return False
   
   # Return true if step excute correcrt all
   return True

async def step_3(context, page, url, job: dict):
    ''' Step 3 are collect and return list of clear queries and handle some common queries like cover letter upload country and number selection. '''
    # temporary save queries and other stuff
    list_of_queries = []
    skip_common_queries = []
    merged_question_text = ""

    # first check if current page of reviews page if yes then we are gonna to submit application
    if '/review' in page.url:
       helper.upload_coverletter_and_submit_application(page)
       helper.append_job_data_in_csv(file_path=config_input.easy_applies_sheet_file_path, data_dict=job)
    
    # return false if in step 3 queries not appears
    if "question" not in page.url:
        logging.critical("In step_3 question are not appeared.")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await page.screenshot(path=f"{config_input.DEBUGGING_SCREENSHOTS_PATH}/queries_not_found_error_{timestamp}.png")
        sys.exit()
        
    # Collect question
    try:
        questions_ele = await page.locator(".ia-Questions-item")
        logger.info(f"{len(questions_ele)} queries collected.")
    except Exception as e:
        logging.warning(f"Error in collecting questions.{e}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await page.screenshot(path=f"{config_input.DEBUGGING_SCREENSHOTS_PATH}/collect_question_error_{timestamp}.png")

    # iterate all question and submit those direct which are common and return only uniques
    for i, question_ele in enumerate(questions_ele):
        
        # Get text frist from question ele
        try:
            logger.info("Iterating questions.")
            question = question_ele.inner_text()
            logger.info("got text from question ele.")
        except Exception as e:
            logger.warning(f"Error in getting text from ele.")
        
        # if question ele don't have type then we are skip
        # If this line is part of a multi-line question (doesn't contain ":Input Field (Type:")
        # and we already have a previous question text being merged
        try:
            if not re.search(r':Input Field \(Type:', question) and merged_question_text:
                # Add this line to the previous question text
                merged_question_text += " " + question
                # Skip the rest of this loop and go to the next question
                continue
        except Exception as e:
            logger.warning(f"Error in check Input Field \(Type: in question ")

        # If there was merged question text from previous lines, use it now
        if merged_question_text:
            question = merged_question_text   # Replace current question with merged text
            merged_question_text = ""              # Reset for next use

        # handle some special question like upload cover letter
        try:
            if await helper.handle_special_questions(question_ele, question, i, skip_common_queries):
                continue
        except Exception as e:
            logger.warning("Error to handle special question.")
        
        # indentify question field input type
        try:
            input_type = "Didn't find field type"
            input_type = await helper.identify_input_type(question)
            logger.info(f"Detected input type: {input_type}")
        except Exception as e:
            logger.warning("Error in indentifying input field types.")
    
        # if input file type did'nt find then skip question
        try:
            if input_type == "Unknown":
                skip_common_queries.append(i)
                continue
        except Exception as e:
            logger.warning(f"Error in appending Unknown input.")

        # append list_of_queries
        try:
            list_of_queries.append(f"\n{question}: {input_type}")
        except Exception as e:
            logger.warning(f"Error in appending list_of_queries.")
        

   # Return true if step excute correct all
    return True


""" This function are submit application."""
async def submitter(easy_applies: List[dict]) -> None:
    logger = setup_logger()

    accounts = await accounts_loader.load_accounts()  # list of accounts    
    async with Stealth().use_async(async_playwright()) as p:
        # create instance of browser with mode headed/headless
        browser = await p.chromium.launch(
            headless=config_input.headless,
            )
        try:
            context = await browser.new_context(viewport=None  # use the full available screen size
                                                )
            await context.add_cookies(random.choice(accounts))
            await _submiting_logic(context, easy_applies)
        except Exception as e:
            logger.exception(f"Context/Listing failed for {easy_applies}: {e}")
        await browser.close()

async def _submiting_logic(context, easy_applies):
    for job in easy_applies:
        page = await context.new_page()
        url = job["url"]
        logger.info(f"Opening {url}")

        try:
            await page.goto(url, wait_until="load")
            step1_result = await step_1(context, page, url)
            if not step1_result:
                await page.close()
                continue

            logger.info("✅ Step 1 done.")

            step1_result = await step_2(context, page, url)
            if not step1_result:
                await page.close()
                continue

            logger.info("✅ Step 2 done.")

            step1_result = await step_3(context, page, url, job)
            if not step1_result:
                await page.close()
                continue

            logger.info("✅ Step 3 done.")

        except Exception as e:
            logger.warning(f"Failed to process {url}: {e}")
        finally:
            await page.close()


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




