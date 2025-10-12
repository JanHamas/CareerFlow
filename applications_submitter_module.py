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
from playwright.async_api import Page, BrowserContext
# await aioconsole.ainput("Press enter")                                                     

# get logger file for saving spider logs.
logger = logging.getLogger("spider")  # use shared logger

async def step_1(step:int, context:BrowserContext, page:Page, url:str, job: dict):
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

async def step_2(step:int, context:BrowserContext, page:Page, url:str, job: dict):
   """
   This one function will be only click buttons for nevigating to question pages.
   """

   # Click on Apply now button
   try:
        await asyncio.sleep(random.uniform(3, 6))
        await page.get_by_text("Apply now", exact=True).click()
        logger.info("Successfully clicked on 'Apply now' button.")
   except Exception as e:
        logger.warning(f"⚠️ Failed to click on 'Apply now' button: {e}")
        return False

    # Wait until new content
   try:
        await page.wait_for_load_state("load", timeout=config_input.wait_for_page_to_load)
        logger.info("Page fully loaded after clicking 'Apply now'.")
   except Exception as e:
        await helper.take_screenshot(page, config_input.DEBUGGING_SCREENSHOTS_PATH, "page_not_load_error")
        logger.warning(f"⚠️ Page did not load within {config_input.wait_for_page_to_load / 1000:.1f}s: {e}")
        return False

    # Continue process
   
   # Click on first continue button
   await helper.click_continue_button(page=page, btn_name="first")

    # Wait until new content
   try:
        await page.wait_for_load_state("load", timeout=config_input.wait_for_page_to_load)
        logger.info("Page fully loaded after clicking 'Apply now'.")
   except Exception as e:
        await helper.take_screenshot(page, config_input.DEBUGGING_SCREENSHOTS_PATH, "page_not_load_error")
        logger.warning(f"⚠️ Page did not load within {config_input.wait_for_page_to_load / 1000:.1f}s: {e}")
        return False

    # Continue process
   

    # Click second continue button 
  
   if "contact-info-module" in page.url:
        await helper.click_continue_button(page=page, btn_name="second")
    
    # Wait until new content
   try:
        await page.wait_for_load_state("load", timeout=config_input.wait_for_page_to_load)
        logger.info("Page fully loaded after clicking 'Apply now'.")
   except Exception as e:
        await helper.take_screenshot(page, config_input.DEBUGGING_SCREENSHOTS_PATH, "page_not_load_error")
        logger.warning(f"⚠️ Page did not load within {config_input.wait_for_page_to_load / 1000:.1f}s: {e}")
        return False


    # Click third continue button 
   if "profile-location" in page.url:
    await helper.click_continue_button(page=page, btn_name="thrid")
    
   # waits until  new page done loading
   try:
       await page.wait_for_load_state("networkidle", timeout= config_input.wait_for_page_to_load)
   except Exception as e:
       await helper.take_screenshot(page, config_input.DEBUGGING_SCREENSHOTS_PATH, "page_not_load_error")
       logger.warning("Page are not loaded.")

   # Click fourth continue button 
   if "resume" in page.url:
        await helper.click_continue_button(page=page, btn_name="fourth")
    
    # Wait for page load or transition
   try:
        await page.wait_for_load_state("load", timeout=config_input.wait_for_page_to_load)
        logger.info("Page fully loaded after clicking 'Apply now'.")
   except Exception as e:
        await helper.take_screenshot(page, config_input.DEBUGGING_SCREENSHOTS_PATH, "page_not_load_error")
        logger.warning(f"⚠️ Page did not load within {config_input.wait_for_page_to_load / 1000:.1f}s: {e}")
        return False

   # Return true if step excute correcrt all.
   return True
    
async def step_3(step:int, context:BrowserContext, page:Page, url:str, job: dict):
    """
    Step 3: Collect and return a list of clear queries and handle common queries like cover letter upload, country, and number selection.
    """

    list_of_queries = []
    skip_common_queries = []
    merged_question_text = ""

    # Check if we're already on the review page
    if '/review' in page.url:
        await helper.upload_coverletter_and_submit_application(page, step=step)
        helper.append_job_data_in_csv(
            file_path=config_input.easy_applies_sheet_file_path,
            data_dict=job
        )
        return [False, [], []]

    # Return False if no question page
    if "questions" not in page.url:
        logger.critical("In step_3, questions did not appear.")
        await helper.take_screenshot(page, config_input.DEBUGGING_SCREENSHOTS_PATH, "quries_not_found_error")
        await page.close()
        return [False, [], []]
    
    # Collect questions
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

    # Iterate through all questions
    for i in range(await questions_ele.count()):
        try:
            question_ele = questions_ele.nth(i)
            question = await question_ele.inner_text()
            logger.info(f"[{i+1}] Got text from question element.")
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
    logger.info(f"{count} Total questions found.")
    logger.info(f"Total queries are for AI Model, some may be skipped: {len(list_of_queries)}\n")
    logger.info(f"List of quries: \n {list_of_queries} \n")
   
    # Return result
    return [True, list_of_queries, skip_common_queries, questions_ele]

async def step_4(step:int, context:BrowserContext, page:Page, url:str, job: dict):
    """
    step 4: this step puting responses of all asked quries in application using AI and also click on next continue button.
    """

    # Check if we're already on the review page.
    if '/review' in page.url:
        await helper.upload_coverletter_and_submit_application(page, step=step)
        helper.append_job_data_in_csv(
            file_path=config_input.easy_applies_sheet_file_path,
            data_dict=job
        )
        return [False, [], []]
   
    # Get list_of_quries from step 3.
    returning_list = await step_3(step, context, page, url, job)
    list_of_quries = returning_list[1]
    skip_common_queries = returning_list[2]
    questions_ele = returning_list[3]
    
    # Now are create form question request.
    request = await helper.creating_form_quries_request(job=job, list_of_queries=list_of_quries)
 
    # Get responses from ai for filling question responses.
    response = await helper.get_form_questions_responses(prompt=request)
    responses = re.findall(r'\d+\.\s*(.+)', response)
    logger.info(f"Cleared and converted to list ai responses: \n {responses}")
    
    # Now let's fill question form.
    await helper.fill_questions_form(page, questions_ele, skip_common_queries, list_of_responses=responses)

    # Once form fill out we need to click on continue button.
    await helper.click_continue_button(page=page, btn_name="form_continue_button")

    # if another question form is aviable after clicking on form then recollect quries and submit.
    try:
        i = 3
        while True:
            i+1 # increment after step 3 because 3 step already done
            if "questions" in page.url:
                await step_3(i, context, page, url, job)
                await step_4(i, context, page, url, job)
            else:
                break
    except Exception as e:
        logger.warning(f"Error in recalling setps function: {e}")
    

async def _submiting_logic(context, easy_applies):
    for job in easy_applies:
        page = await context.new_page()
        url = job["url"]
        logger.info(f"Opened Job : \n {url}")

        try:
            # Opening job link in many try
            for i in range(config_input.try_to_open_page):
                try:
                    await page.goto(url, wait_until="load")
                    break
                except Exception as e:
                    await asyncio.sleep(random.randint(1, 5))
                    logger.warning(f"Faild to load with try {i+1}")
            
            # if step result is true then we move to next step
            step1_result = await step_1(1, context, page, url, job)
            if not step1_result:
                await page.close()
                continue

            logger.info("Step 1 done.")

            # if step result is true then we move to next step
            step2_result = await step_2(2, context, page, url, job)
            if not step2_result:
                await page.close()
                continue

            logger.info("Step 2 done.")

            # if step result is true then we move to next step
            step3_result = await step_3(3, context, page, url, job)
            if step3_result[0] != True:
                await page.close()
                continue

            logger.info("Step 3 done.")

            # if step result is true then we move to next step
            step4_result = await step_4(4, context, page, url, job)
            if step4_result[0]!= True:
                await page.close()
                continue

            logger.info("Step 4 done.")

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




