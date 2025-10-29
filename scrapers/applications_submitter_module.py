import asyncio, random, re, logging
from playwright_stealth import Stealth
from playwright.async_api import async_playwright
from config import config_input
from utils import account_loader, fingerprint_loader, proxies_loader, helper
from typing import List
import pprint
# from utils.logger_setup import setup_logger
import aioconsole
from datetime import datetime
from playwright.async_api import Page, BrowserContext
from utils.bypass import cloudflare
                                                  

# get logger file for saving spider logs.
logger = logging.getLogger("spider")  # use shared logger


async def step_1(step:int, context:BrowserContext, page:Page, url:str, job: dict):
    """
    This function are just confirm some conditions for jobs before further submittions process. 
    """
    # get content of page
    content = await page.content()

    # check if job expired or already applied
    if "<!-- -->This job has expired on Indeed<!-- -->" in content or 'aria-label="Applied "' in content:
        logger.info("Jobs are expired or Applied")
        await helper.take_screenshot(page, config_input.DEBUGGING_SCREENSHOTS_PATH,"applied_or_expired_job")
        await asyncio.sleep(random.randint(2,5))
        return False
    
    # If "Apply now" opens in new tab
    if "Apply now (opens in a new tab)" in content or "Apply on company site" in content:
        await helper.take_screenshot(page, config_input.DEBUGGING_SCREENSHOTS_PATH,"CS_job")
        await asyncio.sleep(random.randint(2,5))
        return False
    
    # Return true if all function are exceute correct. Because then we exceute next step_2 function
    return True


async def step_2(step:int, context:BrowserContext, page:Page, url:str, job: dict):
   """
   This one function will be only click buttons for nevigating to question pages.
   """
   # Click on Apply now button
   try:
        await asyncio.sleep(random.uniform(4, 8))
        btn_name="Apply Now"
        page_old_url = page.url
        await page.get_by_text("Apply now", exact=True).click()
        logger.info("Successfully clicked on 'Apply now' button.")
        # Wait for navigation to success
        navigation_success=await helper.wait_for_page_to_load(page=page, btn_name=btn_name, page_old_url=page_old_url)
        if not navigation_success:
            return False
   except Exception as e:
       logger.warning(f"Error to click on apply now button. {e}")
       return False

   # click on continue button if page is contact form
   if "contact-info-module" in page.url:
        btn_name="contact-info-module"
        page_old_url = page.url
        continue_success=await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        # Check if continue success
        if not continue_success:
            return False
        # Check if navigation success
        navigation_success=await helper.wait_for_page_to_load(page=page, btn_name=btn_name, page_old_url=page_old_url)
        if not navigation_success:
            return False


   # click on profile location continue button if appear
   if "profile-location" in page.url:
        btn_name = "profile-location"
        page_old_url = page.url
        continue_success=await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        # Check if continue success
        if not continue_success:
            return False
        # Check if navigation success
        navigation_success=await helper.wait_for_page_to_load(page=page, btn_name=btn_name, page_old_url=page_old_url)
        if not navigation_success:
            return False


   # Click on continue button if reusme page appear 
   if "resume-selection" in page.url:
        btn_name = "resume"
        page_old_url = page.url
        continue_success=await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        # Check if continue success
        if not continue_success:
            return False
        # Check if navigation success
        navigation_success=await helper.wait_for_page_to_load(page=page, btn_name=btn_name, page_old_url=page_old_url)
        if not navigation_success:
            return False

   # click on continue button if page relevant experience
   if "relevant-experience" in page.url:
        btn_name="relevant-experience"
        page_old_url = page.url
        continue_success=await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        # Check if continue success
        if not continue_success:
            return False
        # Check if navigation success
        navigation_success=await helper.wait_for_page_to_load(page=page, btn_name=btn_name, page_old_url=page_old_url)
        if not navigation_success:
            return False
 
   # Return true if all function are exceute correct. Because then we exceute next step_3 function
   return True
    
async def step_3(step:int, context:BrowserContext, page:Page, url:str, job: dict, result: dict):
    """
    Step 3: Collect and return a list of clear queries and handle common queries like cover letter upload, country, and number selection.
    """
    # Check if we're already on the review page
    if 'review-module' in page.url:
        await page.wait_for_selector("text='Submit your application'", timeout=config_input.wait_for_review_page_loading)
        btn_name="submit application button"
        continue_success=await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        # Check if continue success
        if not continue_success:
            return False


    # Return False if no question page
    if "questions" not in page.url:
        logger.critical("In step_3, questions did not appear.")
        await helper.take_screenshot(page, config_input.DEBUGGING_SCREENSHOTS_PATH, "quries_not_page_error")
        await page.close()
        return False
    
    # Collect questions
    try:
        questions_ele = page.locator(".ia-Questions-item")
        count = await questions_ele.count()
    except Exception as e:
        logger.warning(f"Error in collecting questions: {e}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await page.screenshot(
            path=f"{config_input.DEBUGGING_SCREENSHOTS_PATH}/collect_questions_error_{timestamp}.png")
        return False
    

    # fill out list for give response of form
    list_of_queries = []
    skip_common_queries = []
    merged_question_text = ""
    
    question_number = 1
    # Iterate through all questions
    for i in range(await questions_ele.count()):
        try:
            # Convert Locator → ElementHandle
            question_ele = await questions_ele.nth(i).element_handle()
            question = await question_ele.inner_text()
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
        except Exception as e:
            # logger.warning(f"Error identifying input field type: {e}")
            input_type = "Unknown"

        if input_type == "Unknown":
            skip_common_queries.append(i)
            continue

        # Append result
        list_of_queries.append(f"{question_number}: {input_type} : {question}")
        question_number+=1
    
    # if quries not page in page then click on continue button and recall step 3 method.
    if len(list_of_queries) == 0:
        logger.info("No questions found — clicking continue.")
        page_old_url = page.url
        btn_name  = "0 quries page continue"
        continue_success=await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        # Check if continue success
        if not continue_success:
            return False
        # Check if navigation success
        navigation_success=await helper.wait_for_page_to_load(page=page, btn_name=btn_name, page_old_url=page_old_url)
        if not navigation_success:
            return False
        return await step_3(str(int(step)+1), context, page, url, job, result)
    else:
        logger.info(f"{count}: Total quries found.")
        # convert all \n to new lines
        cleaned_list = [item.replace("\xa0", "").replace("\n", "").replace("\\n", "").strip() for item in list_of_queries]
        # Make list format pretty well ok.
        formatted_quries = pprint.pformat(cleaned_list, indent=3, width=120)
        # Log formated and clean list
        logger.info(f"Form quries list for ai: Length {len(formatted_quries)} \n {formatted_quries}")
    
    # With share state techniques share result data with another function.
    result["list_of_queries"] = formatted_quries
    result["skip_common_queries"] = skip_common_queries
    result["questions_ele"] = questions_ele

    # Return result
    return True

async def step_4(step:int, context:BrowserContext, page:Page, url:str, job: dict, result_data:dict ):
    """
    step 4: this step puting responses of all asked quries in application using AI and also click on next continue button if other quries aviable in app they are also handle those by calling again step_3 fucntion for collecting quries.
    """

    # Check if we're already on the review page.
    if 'review-module' in page.url:
        await page.wait_for_selector("text='Submit your application'", timeout=config_input.wait_for_review_page_loading)
        btn_name="submit your application"
       
        continue_success=await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        # Check if continue success
        if not continue_success:
            return False
   
    # result_data dictionay are returned by step with data for further process
    try:
        list_of_queries = result_data["list_of_queries"]
        skip_common_queries = result_data["skip_common_queries"]
        questions_ele = result_data["questions_ele"]
    except Exception as e:
        logger.critical(f"Error in accessing value step 3 returned dict: {e}")


    # Now are create form question request.
    prompt = await helper.create_form_quries_prompt(job=job, list_of_queries=list_of_queries)
 
    # Get responses from ai for filling question responses.
    response = await helper.get_form_questions_and_coverletter_responses(prompt=prompt)
    
    # Clean and convert ai response for filling form.
    try:
        # Improved pattern to handle empty responses and capture properly
        pattern = r'^\s*(\d+)\.\s*(.*?)\s*(?=\n\s*\d+\.|\n\s*$|$)'
        matches = re.findall(pattern, response, re.MULTILINE | re.DOTALL)
        # Create a dictionary to ensure we get all numbers in sequence
        responses_dict = {int(num): ans.strip() for num, ans in matches}
        # Find the maximum question number to ensure we have all slots
        max_question = max(responses_dict.keys()) if responses_dict else 0
        # Build the response list in order, ensuring all positions are filled
        responses = []
        for i in range(1, max_question + 1):
            responses.append(responses_dict.get(i, ''))  # Empty string for missing numbers
        logger.info(f"Cleared and converted to list ai response. len({len(responses)}): \n {responses}")
    except Exception as e:
        logger.info(f"Error in cleaning ai response: {e}")

   
    # Now let's fill question form.
    try:
        await helper.fill_questions_form(page, questions_ele, skip_common_queries,responses)
        # Once form fill out we need to click on continue button.
        btn_name="form_continue_button near to fill_question"
        # Get first current page url to check later for changing.
        page_old_url = page.url
        continue_success=await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        # Check if continue success
        if not continue_success:
            return False
        # Check if navigation success
        navigation_success=await helper.wait_for_page_to_load(page=page, btn_name=btn_name, page_old_url=page_old_url)
        if not navigation_success:
            return False
    except Exception as e:
        logger.warning(f"Error in quries filling block: {e}")

    # if another question form is aviable after clicking on continue then recollect quries and submit with responses.
    i = 3
    while "questions" in page.url:
        i += 1
        result_data = {}
        result = await step_3(i, context, page, url, job, result_data)
        if not result:
            break
        await step_4(i, context, page, url, job, result_data)
        # click and wait for page to load
        btn_name="form_continue_button near to questions"
        page_old_url = page.url
        continue_success=await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        # Check if continue success
        if not continue_success:
            return False
        # Check if navigation success
        navigation_success=await helper.wait_for_page_to_load(page=page, btn_name=btn_name, page_old_url=page_old_url)
        if not navigation_success:
            return False


async def _submiting_logic(context, easy_applies):
    try:
        for job in easy_applies:
            page = await context.new_page()
            url = job["url"]
            logger.info(f"Opened Job for application submittion: \n {url}")
          
            # Opening job link in many try
            for i in range(config_input.try_to_open_page):
                try:
                    await page.goto(url, wait_until="load")
                    break
                except Exception as e:
                    logger.warning(f"Failed to load {url} (try {i+1}): {e}")
                    # if job url page not load in many time then try to another.
                    if i != config_input.try_to_open_page-1:
                        # Open a new page
                        page2 = await context.new_page()
                        await page2.goto("https://example.com", wait_until="load")
                        # Close the old page (first one)
                        for p in context.pages:
                            if p != page2:
                                await p.close()
                        # Assign new page to `page` so next loop iteration uses it
                        page = page2  
                        logger.info("Waiting before retry...")
                        await asyncio.sleep(random.randint(3, 7))

            #check and bypass if cloudflare captcha appear
            try:
                cf_bypasser = cloudflare.CloudflareBypasser(page)
                await cf_bypasser.detect_and_bypass()
            except Exception as e:
                logger.error(f"Captcha error: {e}")
                logger.info("Cloudflare did'n't bypass so let's navigate.")
                continue

            # if step result is true then we move to next step
            result = await step_1(1, context, page, url, job)
            if not result:
                await page.close()
                continue

            logger.info("Successfully complete step 1.")

            # if step result is true then we move to next step
            result = await step_2(2, context, page, url, job)
            if not result:
                await page.close()
                continue

            logger.info("Successfully complete step 2.")

            # if step result is true then we move to next step
            result_data = {}
            result = await step_3(3, context, page, url, job, result_data)
            if not result:
                await page.close()
                continue

            logger.info("Successfully complete step 3.")

            # if step result is true then we move to next step
            result = await step_4(4, context, page, url, job, result_data)
            if not result:
               await page.close()
               continue

            logger.info("All jobs submit successfully.")
    except Exception as e:
        logger.warning(f"Failed to process {url}: {e}")
    finally:
        if 'page' in locals() and not page.is_closed():
            await page.close()


# Fake easy_applies data (same structure as the extractor output)
# fake_easy_applies =[
#  {
#     "company_name": "Prospance Inc",
#     "url": "https://indeed.com/rc/clk?jk=728290722593f9bd&bb=olP8tuAQAe7oclzPrBjqyDQCjEZ-HjBZJMyLj15V193FbFDfjJ9VUeLN3ZHLWjQ9VT_ugyYnkmWMKCCWTHbo7Q3nPOR3MwrXNC7VTv4BIN9PWOPmiY07PO0uxcu82DWW&xkcb=SoBy67M3s42c8Dzb7p0JbzkdCdPP&fccid=d86a3205ba0b6180&vjs=3",
#     "matching_per": "89%",
#     "job_title": "Data Engineer",
#     "salary": "$140k",
#     "job_other_details": "Full-time · SQL/Python/AWS",
#     "benefits": "Flexible hours, remote option",
#     "full_description": "Manage data pipelines and optimize ETL processes."
#   },
#   {
#     "company_name": "ICURO",
#     "url": "https://indeed.com/rc/clk?jk=2d9ad5f5e2f65995&bb=ByMXxTaMajrbMuwx72Z2ovI5huspN-LUKvdcMlwLb9NCRlfdyxXqJtO3_P99LX9VMv30Hgk4_V9sATv23aGLH9Ot0ppokIAWQvwxPhPDJT1rgZo4fPufhjViWI1UIHfM3VXrMPPHvSFUBUov0HltvQ%3D%3D&xkcb=SoDE67M3s42Skrywwx0MbzkdCdPP&fccid=9fbba4565e7dbe3a&vjs=3",
#     "matching_per": "91%",
#     "job_title": "Machine Learning Engineer",
#     "salary": "$150k",
#     "job_other_details": "Full-time · Deep Learning/NLP",
#     "benefits": "Stock options, health coverage",
#     "full_description": "Build and optimize ML models for healthcare analytics."
#   },
#   {
#     "company_name": "Avanza",
#     "url": "https://indeed.com/rc/clk?jk=1b0420003e1eea3d&bb=K5xWk6PHJKSNq1m0UtmYaCpe7R_uboEnLpMPKCds0QXHZPuion6NvTKf9YRlTyhk5b-T5TA5MO5vewCK9hY_CmOBB5kziJIVZENF1G9h9NmM2o_SuPTrPgdYb4IMZymt4aelsIQYI7ngauBeK1bDdg%3D%3D&xkcb=SoB367M3s42-eEQpR50JbzkdCdPP&fccid=9ac68eefd24f53c5&vjs=3",
#     "matching_per": "94%",
#     "job_title": "AI Architect",
#     "salary": "$160k",
#     "job_other_details": "Full-time · Remote · AI Solutions",
#     "benefits": "Remote, paid leave, healthcare",
#     "full_description": "Architect AI-driven platforms for enterprise clients."
#   },
 
#   {
#     "company_name": "Incoexco",
#     "url": "https://indeed.com/rc/clk?jk=33bfda2c27d1794e&bb=K5xWk6PHJKSNq1m0UtmYaDJcDJrrpWCbDL_knLCRYudYq6u4AUkUdtegFPKRm8-yjLDB39IrRYqXy-c3y0FasUT2guCBReh_LX5RS-mKc7NYkR_iktcF743Fc27orBoU0NsnJD2jb3MOqz3d6Z0FVQ%3D%3D&xkcb=SoBN67M3s42-eEQpR50PbzkdCdPP&fccid=2e3f36bc3cf64031&vjs=3",
#     "matching_per": "95%",
#     "job_title": "Python Developer",
#     "salary": "$135k",
#     "job_other_details": "Full-time · Django/Flask",
#     "benefits": "Health insurance, WFH",
#     "full_description": "Develop APIs and backend systems in Python."
#   },
# ]


""" This function are submit application. """
async def submitter(easy_applies: List[dict]) -> None:
    # logger = setup_logger()

    indeed_account = await account_loader.load_account(config_input.INDEED_ACCOUNT_DIR_FOR_APP_SUBMISSION)  # load indeed account in json format. 
    
    # Start playwright with stealty(undetectable) mode.
    async with Stealth().use_async(async_playwright()) as p:
        # create instance of browser with mode headed/headless
        browser = await p.chromium.launch(
            headless=config_input.headless_for_app_submittion,
            args=["--start-maximized"]
            )
        try:
            context = await browser.new_context(no_viewport=True)
            await context.add_cookies(indeed_account)
            await _submiting_logic(context, easy_applies)
        except Exception as e:
            logger.exception(f"Context/Listing failed for {easy_applies}: {e}")
        await browser.close()

# # Run the submitter function to test
# async def main():
#     await submitter(easy_applies=fake_easy_applies)

# asyncio.run(main())




