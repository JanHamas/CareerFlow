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
    """
    This function are just confirm some conditions for jobs before further submittions process. 
    """

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
   """
   This one function will be only click buttons for nevigating to question pages.
   """
   # Click on Apply now button
   try:
       await page.get_by_text("Apply now").click()
       logger.info("Successfuly Click on Apply now button.")
   except Exception as e:
       logger.info("Failed to click on first continue button.")
       return False
   
   # Click first continue button
   await helper.click_continue_button(page=page, btn_name="frist")
  
   # Click second continue button 
   if "contact-info-module" in page.url:
        await helper.click_continue_button(page=page, btn_name="second")
        await asyncio.sleep(3)
   
   # Click third continue button 
   if "profile-location" in page.url:
    await helper.click_continue_button(page=page, btn_name="thrid")
    await asyncio.sleep(3)
    
   # Click fourth continue button 
   if "resume" in page.url:
        await helper.click_continue_button(page=page, btn_name="fourth")

   # Return true if step excute correcrt all
   return True
    
async def step_3(context, page, url, job: dict):
    """
    Step 3: Collect and return a list of clear queries and handle common queries like cover letter upload, country, and number selection.
    """
    list_of_queries = []
    skip_common_queries = []
    merged_question_text = ""

    # Check if we're already on the review page
    if '/review' in page.url:
        await helper.upload_coverletter_and_submit_application(page)
        helper.append_job_data_in_csv(
            file_path=config_input.easy_applies_sheet_file_path,
            data_dict=job
        )
        return [False, [], []]

    # Return False if no question page
    await asyncio.sleep(5)
    if "questions" not in page.url:
        logger.critical("In step_3, questions did not appear.")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await page.screenshot(
            path=f"{config_input.DEBUGGING_SCREENSHOTS_PATH}/queries_not_found_error_{timestamp}.png", full_page=True        )
        await aioconsole.ainput("Press enter")
        return [False, [], []]

    # ✅ Collect questions
    try:
        questions_ele = page.locator(".ia-Questions-item")
        count = await questions_ele.count()
        logger.info(f"{count} queries collected.")
    except Exception as e:
        logger.warning(f"Error in collecting questions: {e}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await page.screenshot(
            path=f"{config_input.DEBUGGING_SCREENSHOTS_PATH}/collect_questions_error_{timestamp}.png"
        )
        return [False, [], []]

    # ✅ Iterate through all questions
    for i in range(await questions_ele.count()):
        try:
            question_ele = questions_ele.nth(i)
            question = await question_ele.inner_text()
            logger.info(f"[{i}] Got text from question element.")
        except Exception as e:
            logger.warning(f"Error getting text from element: {e}")
            continue

        # Merge multi-line questions
        if not re.search(r':Input Field \(Type:', question) and merged_question_text:
            merged_question_text += " " + question
            continue

        if merged_question_text:
            question = merged_question_text
            merged_question_text = ""

        # Handle special questions
        try:
            if await helper.handle_special_questions(page, question_ele, question, i, skip_common_queries):
                continue
        except Exception as e:
            logger.warning(f"Error handling special question: {e}")
            
        # Identify input type
        try:
            input_type = await helper.identify_input_type(question_ele)
            logger.info(f"Detected input type: {input_type}")
        except Exception as e:
            logger.warning(f"Error identifying input field type: {e}")
            input_type = "Unknown"

        if input_type == "Unknown":
            skip_common_queries.append(i)
            continue

        # Append result
        list_of_queries.append(f"\n{question}: {input_type}")
    
    # print info about collected jobs\
    logger.info(f"{len(count)} Total questions found.")
    logger.info(f"Total queries are for AI Model, some may be skipped: {len(list_of_queries)}")
   
    # ✅ Return result
    return [True, list_of_queries, skip_common_queries]

async def step_4(context, page, url, job: dict):
    """
    step 4: this step puting responses of all asked quries in application using AI and also click on next continue button.
    """
    # Check if we're already on the review page
    if '/review' in page.url:
        await helper.upload_coverletter_and_submit_application(page)
        helper.append_job_data_in_csv(
            file_path=config_input.easy_applies_sheet_file_path,
            data_dict=job
        )
        return [False, [], []]
    
    # Check if step_3 function not return list_of_quries then return ture because some page don't have question)
    returning_list = await step_3()
    if len(returning_list[1]) <= 0:
        logger.info("Zero question found in page.")
        # take a screen shot from that
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await page.screenshot(
            path=f"{config_input.DEBUGGING_SCREENSHOTS_PATH}/zero_queries_found_{timestamp}.png")
        return True
    
    # Now are create form question request
    request = await helper.get_form_questions_request(list_of_queries=returning_list[1])
    # Get responses from ai for filling question responses
    responses = await helper.get_question_responses(prompt=request)

async def _submiting_logic(context, easy_applies):
    for job in easy_applies:
        page = await context.new_page()
        url = job["url"]
        logger.info(f"Opened Job : \n {url}")

        try:
            await page.goto(url, wait_until="load")
            step1_result = await step_1(context, page, url)
            if not step1_result:
                await page.close()
                continue

            logger.info("✅ Step 1 done.")

            step2_result = await step_2(context, page, url)
            if not step2_result:
                await page.close()
                continue

            logger.info("✅ Step 2 done.")

            step3_result = await step_3(context, page, url, job)
            if True not in step3_result:
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

""" This function are submit application. """
async def submitter(easy_applies: List[dict]) -> None:
    logger = setup_logger()

    accounts = await accounts_loader.load_accounts()  # list of accounts    
    async with Stealth().use_async(async_playwright()) as p:
        # create instance of browser with mode headed/headless
        browser = await p.chromium.launch(
            headless=False,
            )
        try:
            context = await browser.new_context(viewport=None  # use the full available screen size
                             )
            await context.add_cookies(random.choice(accounts))
            await _submiting_logic(context, easy_applies)
        except Exception as e:
            logger.exception(f"Context/Listing failed for {easy_applies}: {e}")
        await browser.close()

# Run the submitter function to test
async def main():
    await submitter(easy_applies=fake_easy_applies)

asyncio.run(main())




