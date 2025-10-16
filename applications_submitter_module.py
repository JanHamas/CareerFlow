import asyncio, random, re, logging
from playwright_stealth import Stealth
from playwright.async_api import async_playwright
from config import config_input
from utils import accounts_loader, fingerprint_loader, proxies_loader, helper
from typing import List
from utils.logger_setup import setup_logger
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
    if "This job has expiredd" in content or 'aria-label="Applied "' in content:
        logger.info("Jobs are expired or Applied")
        await helper.take_screenshot(page, config_input.DEBUGGING_SCREENSHOTS_PATH,"applied_or_expired_job")
        await asyncio.sleep(random.randint(2,5))
        return False
    
    # If "Apply now" opens in new tab
    if "Apply now (opens in a new tab)" in content:
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
   for i in range(3):
       try:
            await asyncio.sleep(random.uniform(3, 6))
            await page.get_by_text("Apply now", exact=True).click()
            logger.info("Successfully clicked on 'Apply now' button.")
            btn_name="Apply Now"
            current_url = page.url
            await helper.wait_for_page_to_load(page=page, btn_name=btn_name, current_url=current_url)
            break
       except Exception as e:
            logger.warning(f"Attempt {i+1} failed: {e}")
            logger.info("Page reload.")
            await page.reload()
            if i == 2:
                return False
            continue
   
      
   # click on continue button if page is contact form
   if "contact-info-module" in page.url:
        btn_name="contact-info-module"
        current_url = page.url
        await helper.click_continue_button(page=page, btn_name=btn_name, job=job)
        await helper.wait_for_page_to_load(page=page, btn_name=btn_name, current_url=current_url)

   # click on profile location continue button if appear
   if "profile-location" in page.url:
        btn_name = "profile-location"
        current_url = page.url
        await helper.click_continue_button(page=page, btn_name=btn_name, job=job)
        await helper.wait_for_page_to_load(page=page, btn_name=btn_name, current_url=current_url)

   # Click on continue button if reusme page appear 
   if "resume-selection" in page.url:
        btn_name = "resume"
        current_url = page.url
        await helper.click_continue_button(page=page, btn_name=btn_name, job=job)
        await helper.wait_for_page_to_load(page=page, btn_name=btn_name, current_url=current_url)


   # click on continue button if page relevant experience
   if "relevant-experience" in page.url:
        btn_name="relevant-experience"
        current_url = page.url
        await helper.click_continue_button(page=page, btn_name=btn_name, job=job)
        await helper.wait_for_page_to_load(page=page, btn_name=btn_name, current_url=current_url)
 
   # Return true if all function are exceute correct. Because then we exceute next step_3 function
   return True
    
async def step_3(step:int, context:BrowserContext, page:Page, url:str, job: dict):
    """
    Step 3: Collect and return a list of clear queries and handle common queries like cover letter upload, country, and number selection.
    """

    # Check if we're already on the review page
    if 'review-module' in page.url:
        await asyncio.sleep(5)
        btn_name="review application"
        await helper.click_continue_button(page=page, btn_name=btn_name, job=job)
        
        return [False, [], []]

    # Return False if no question page
    if "questions" not in page.url:
        logger.critical("In step_3, questions did not appear.")
        await helper.take_screenshot(page, config_input.DEBUGGING_SCREENSHOTS_PATH, "quries_not_page_error")
        await page.close()
        return [False, [], []]
    
    # Collect questions
    try:
        questions_ele = page.locator(".ia-Questions-item")
        count = await questions_ele.count()
    except Exception as e:
        logger.warning(f"Error in collecting questions: {e}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await page.screenshot(
            path=f"{config_input.DEBUGGING_SCREENSHOTS_PATH}/collect_questions_error_{timestamp}.png"
        )
        return [False, [], []]

    # fill out list for give response of form
    list_of_queries = []
    skip_common_queries = []
    merged_question_text = ""

    # Iterate through all questions
    for i in range(await questions_ele.count()):
        try:
            # Convert Locator → ElementHandle
            question_ele = await questions_ele.nth(i).element_handle()
            question = await question_ele.inner_text()
            # logger.info(f"Element {i+1} text : {question}")
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
            logger.info("Checking for common quries...")
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
        list_of_queries.append(f"{i+1}\n{question}: {input_type}")
    
    # if quries not page in page then click on continue button and recall step 3 method
    if len(list_of_queries) == 0:
        logger.info("No questions found — clicking continue.")
        current_url = page.url
        btn_name  = "0 quries page continue"
        await helper.click_continue_button(page=page, btn_name=btn_name, job=job)
        await helper.wait_for_page_to_load(page=page, btn_name=btn_name, current_url=current_url)
        return await step_3(step + 1, context, page, url, job)
    else:
        logger.info(f"{count}: Total quries found.")
        logger.info(f"Form quries list for ai: Length {len(list_of_queries)} \n {list_of_queries}")

    # Return result
    return [True, list_of_queries, skip_common_queries, questions_ele]

async def step_4(step:int, context:BrowserContext, page:Page, url:str, job: dict, step3_return_list_of_quries):
    """
    step 4: this step puting responses of all asked quries in application using AI and also click on next continue button.
    """

    # Check if we're already on the review page.
    if 'review-module' in page.url:
        await asyncio.sleep(5)
        btn_name="review application"
        await helper.click_continue_button(page=page, btn_name=btn_name, job=job)
        
        return [False, [], []]
   

    # Get list_of_quries, skiping_list, questions_ele from step_3 function
    returning_list = step3_return_list_of_quries
    list_of_quries = returning_list[1]
    skip_common_queries = returning_list[2]
    questions_ele = returning_list[3]
    
    # Now are create form question request.
    request = await helper.creating_form_quries_request(job=job, list_of_queries=list_of_quries)
 
    # Get responses from ai for filling question responses.
    response = await helper.get_form_questions_responses(prompt=request)
    responses = re.findall(r'\d+\.\s*(.+)', response)
    logger.info(f"Cleared and converted to list ai response: len({len(responses)}): \n {responses}")
    
    # Now let's fill question form.
    try:
        await helper.fill_questions_form(page, questions_ele, skip_common_queries,responses)
        # Once form fill out we need to click on continue button.
        btn_name="form_continue_button"
        current_url = page.url
        await helper.click_continue_button(page=page, btn_name=btn_name, job=job)
        await helper.wait_for_page_to_load(page, btn_name=btn_name, current_url=current_url)
    except Exception as e:
        logger.warning(f"Error in quries filling block: {e}")

    # if another question form is aviable after clicking on continue then recollect quries and submit with responses.
    i = 3
    while "questions" in page.url:
        i += 1
        new_return_list = await step_3(i, context, page, url, job)
        if not new_return_list[0]:
            break
        await step_4(i, context, page, url, job, new_return_list)
        # click and wait for page to load
        btn_name="form_continue_button"
        current_url = page.url
        await helper.click_continue_button(page=page, btn_name=btn_name, job=job)
        await helper.wait_for_page_to_load(page, btn_name=btn_name, current_url=current_url)

    
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
                    logger.warning(f"Failed to load {url} (try {i+1}): {e}")

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
            return_list = await step_3(3, context, page, url, job)
            if return_list[0] != True:
                await page.close()
                continue

            logger.info("Step 3 done.")

            # if step result is true then we move to next step
            step4_result = await step_4(4, context, page, url, job, return_list)
            if step4_result[0]!= True:
                await page.close()
                continue

            logger.info("All jobs submit successfully.")

        except Exception as e:
            logger.warning(f"Failed to process {url}: {e}")
        finally:
            await page.close()

# Fake easy_applies data (same structure as the extractor output)
fake_easy_applies = [
    
    {
        "company_name": "Netflix",
        "url": "https://indeed.com/rc/clk?jk=27b34ccaa37f63ab&bb=acxJRK-Q95RApR66Q4NVthjCii42RRxtgvkDBIFsGV21XGa_doPo-TNF0XbBHh__Hw6Emcpd1jm9vwk5FUWhFl4UpedWRVXZtPY9E9F1yZPm6ETIQt060DcI4mqeyaqa&xkcb=SoDW67M3sz_7lNyNhp0PbzkdCdPP&fccid=93aad9f3276f47ef&vjs=3",
        "matching_per": "92%",
        "job_title": "Frontend Engineer",
        "salary": "$130k",
        "job_other_details": "Full-time · React/TypeScript",
        "benefits": "Health, flexible hours",
        "full_description": "Work on the UI of streaming apps."
    },
    {
        "company_name": "Netflix",
        "url": "https://indeed.com/rc/clk?jk=32f0d11caa2e8e0b&bb=jt58q0wX8nGWSt78qAKYAYQcr2CwS4aVajz1HDqr7AwRi9iyynxbDWCthkbaLdLByR9DRwLpBoxq6Ft3WBpgFT56VddzAFap1d6vSGGJN75b4jLEV9rSof_ciBTKza8Nm-rSNKKLbDM%3D&xkcb=SoAu67M3sz_-EVTbxh0LbzkdCdPP&fccid=47875013cd33242a&vjs=3",
        "matching_per": "92%",
        "job_title": "Frontend Engineer",
        "salary": "$130k",
        "job_other_details": "Full-time · React/TypeScript",
        "benefits": "Health, flexible hours",
        "full_description": "Work on the UI of streaming apps."
    },
   
   {
        "company_name": "Netflix",
        "url": "https://indeed.com/rc/clk?jk=d096ae5e6aea69e2&bb=EO40NAHh-L585rOFOC8TZMblWzxzllgGRb0CvyK4EpdmSgoeyvRlqyfQv3N-_AphQx7Iv4MqNpMO4V06HLRV4eMgUzZICPyDtCKnc99RQP1mmjqN_bACIcBdaxzcgJhpR5jhG4zk08I%3D&xkcb=SoDu67M3sz_k3_TblZ0PbzkdCdPP&fccid=31e292c1c5683b52&cmp=Rediantt&ti=Machine+Learning+Engineer&vjs=3",
        "matching_per": "92%",
        "job_title": "Frontend Engineer",
        "salary": "$130k",
        "job_other_details": "Full-time · React/TypeScript",
        "benefits": "Health, flexible hours",
        "full_description": "Work on the UI of streaming apps."
    },
   
   {
        "company_name": "Netflix",
        "url": "https://indeed.com/rc/clk?jk=9f5835204b532e6f&bb=EO40NAHh-L585rOFOC8TZMWtL4Yf-OGOaWjDuvErasBEvmYT_9aKkE80_JGUTX68f-7YeBtvlvgRQWO1as64FYkj9uH4z80IJOB97F1sQ3E2qbahsj_y-cnL2TUBsaEYfYnZC5nRNcs%3D&xkcb=SoBg67M3sz_k3_TblZ0IbzkdCdPP&fccid=18ab0cdb22460bcf&vjs=3",
        "matching_per": "92%",
        "job_title": "Frontend Engineer",
        "salary": "$130k",
        "job_other_details": "Full-time · React/TypeScript",
        "benefits": "Health, flexible hours",
        "full_description": "Work on the UI of streaming apps."
    },
       {
        "company_name": "Netflix",
        "url": "https://indeed.com/rc/clk?jk=6c47b64ebe452240&bb=EO40NAHh-L585rOFOC8TZOpL-c4Ei4P-hDQlOMKBb-zOe2BrEXwjhTngGy9ijf_uZTQ38n6pkHSF7y0Q3cgtUNStNeARnQnfsIEcW43hMSJnW-fAP_OSJHFUcaEogguVpV4bR2NkBLk%3D&xkcb=SoDU67M3sz_k3_TblZ0JbzkdCdPP&fccid=e732a9e107b73483&vjs=3",
        "matching_per": "92%",
        "job_title": "Frontend Engineer",
        "salary": "$130k",
        "job_other_details": "Full-time · React/TypeScript",
        "benefits": "Health, flexible hours",
        "full_description": "Work on the UI of streaming apps."
    },
   
   
    
]

""" This function are submit application. """
async def submitter(easy_applies: List[dict]) -> None:
    logger = setup_logger()

    accounts = await accounts_loader.load_accounts()  # list of accounts    
    async with Stealth().use_async(async_playwright()) as p:
        # create instance of browser with mode headed/headless
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized"]
            )
        try:
            context = await browser.new_context(no_viewport=True  # use the full available screen size
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




