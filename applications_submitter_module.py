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
   await asyncio.sleep(random.uniform(4, 8))
   await page.get_by_text("Apply now", exact=True).click()
   logger.info("Successfully clicked on 'Apply now' button.")
   btn_name="Apply Now"
   current_url = page.url
   await helper.wait_for_page_to_load(page=page, btn_name=btn_name, current_url=current_url)
   

   # click on continue button if page is contact form
   if "contact-info-module" in page.url:
        btn_name="contact-info-module"
        current_url = page.url
        await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        await helper.wait_for_page_to_load(page=page, btn_name=btn_name, current_url=current_url)


   # click on profile location continue button if appear
   if "profile-location" in page.url:
        btn_name = "profile-location"
        current_url = page.url
        await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        await helper.wait_for_page_to_load(page=page, btn_name=btn_name, current_url=current_url)


   # Click on continue button if reusme page appear 
   if "resume-selection" in page.url:
        btn_name = "resume"
        current_url = page.url
        await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        await helper.wait_for_page_to_load(page=page, btn_name=btn_name, current_url=current_url)


   # click on continue button if page relevant experience
   if "relevant-experience" in page.url:
        btn_name="relevant-experience"
        current_url = page.url
        await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        await helper.wait_for_page_to_load(page=page, btn_name=btn_name, current_url=current_url)
 
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
        await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
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
        list_of_queries.append(f"{i+1}\n{question}: {input_type}")
    
    # if quries not page in page then click on continue button and recall step 3 method
    if len(list_of_queries) == 0:
        logger.info("No questions found — clicking continue.")
        current_url = page.url
        btn_name  = "0 quries page continue"
        await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        await helper.wait_for_page_to_load(page=page, btn_name=btn_name, current_url=current_url)
        return await step_3(str(int(step)+1), context, page, url, page, url, job, result)
    else:
        logger.info(f"{count}: Total quries found.")
        logger.info(f"Form quries list for ai: Length {len(list_of_queries)} \n {list_of_queries}")
    
    # With share state techniques share result data with another function.
    result["list_of_queries"] = list_of_queries
    result["skip_common_queries"] = skip_common_queries
    result["questions_ele"] = questions_ele

    
    # Return result
    return True


async def step_4(step:int, context:BrowserContext, page:Page, url:str, job: dict, result_data:dict ):
    """
    step 4: this step puting responses of all asked quries in application using AI and also click on next continue button.
    """

    # Check if we're already on the review page.
    if 'review-module' in page.url:
        await page.wait_for_selector("text='Submit your application'", timeout=config_input.wait_for_review_page_loading)
        btn_name="submit your application"
        await helper.click_continue_button(page=page, btn_name=btn_name, step="4", job=job)
        
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
    responses = re.findall(r'\d+\.\s*(.*)', response)
    logger.info(f"Cleared and converted to list ai response. len({len(responses)}): \n {responses}")
    
    # Now let's fill question form.
    try:
        await helper.fill_questions_form(page, questions_ele, skip_common_queries,responses)
        # Once form fill out we need to click on continue button.
        btn_name="form_continue_button"
        current_url = page.url
        await helper.click_continue_button(page=page, btn_name=btn_name, step=step, job=job)
        await helper.wait_for_page_to_load(page, btn_name=btn_name, current_url=current_url)
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
        btn_name="form_continue_button"
        current_url = page.url
        await helper.click_continue_button(page=page, btn_name=btn_name, step=str(i), job=job)
        await helper.wait_for_page_to_load(page, btn_name=btn_name, current_url=current_url)

    
async def _submiting_logic(context, easy_applies):
    try:
        for job in easy_applies:
            page = await context.new_page()
            url = job["url"]
            logger.info(f"Opened Job : \n {url}")
          
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
fake_easy_applies =[
  {
    "company_name": "Netflix",
    "url": "https://indeed.com/rc/clk?jk=51f7cc6a4a9389d6&bb=leBa_oZfDp3YEVBO8KtWHLWbtN6W-T6vw_MW5aBljMZZ3UMrlsD0h_SM3SYGSuSQEq6LjfL5JRhB_2WmGsBd-z3h0c1ZXV8Ku4iUx98JcHp7k7O6_3dQGhG_tXCZdF6B&xkcb=SoCf67M3s41033A8-b0ObzkdCdPP&fccid=2973259ddc967948&vjs=3",
    "matching_per": "92%",
    "job_title": "Frontend Engineer",
    "salary": "$130k",
    "job_other_details": "Full-time · React/TypeScript",
    "benefits": "Health, flexible hours",
    "full_description": "Work on the UI of streaming apps."
  },
  {
    "company_name": "MeetyourVA",
    "url": "https://indeed.com/rc/clk?jk=4865a6baa0c9d259&bb=IumWtt_fBnPvYcobRpO73HFjsbvl4Ovh_TnWg8nijlNuxR6mZNpFj-OilomtqTJIQlRj77Q5DG_rLVWFjHubgELoLLEs_lC1pvax6fIYY6yEp5VwP6hah8Y6auw9ZJZB&xkcb=SoBR67M3s42IzY3YtR0IbzkdCdPP&fccid=cdf20941eab1a5eb&cmp=MeetyourVA&ti=Solutions+Engineer&vjs=3",
    "matching_per": "85%",
    "job_title": "Solutions Engineer",
    "salary": "$115k",
    "job_other_details": "Remote · Full-time",
    "benefits": "Health, dental, 401k",
    "full_description": "Collaborate with clients to build scalable solutions."
  },
  {
    "company_name": "Hanosys Inc",
    "url": "https://indeed.com/rc/clk?jk=ec2dfea933ea63a4&bb=iaeA_7VV77p9mQuXnUSmSsjZRMKJplkkcybwXZ1CR_XTooeLt6V4dBwBfHrBeByEtP-3WgAPClzS6aNAh4COibKLIz_upPhfWTl_V0alqB6CNSOJjAWtrFh6VRqmEnBo0xZscMrbOIk%3D&xkcb=SoDC67M3s42WqK20AJ0FbzkdCdPP&fccid=b9a626903ceeba97&cmp=Hanosys.inc&ti=Ai%2Fml+Engineer&vjs=3",
    "matching_per": "88%",
    "job_title": "AI/ML Engineer",
    "salary": "$145k",
    "job_other_details": "Full-time · TensorFlow/Python",
    "benefits": "Remote work, paid vacation",
    "full_description": "Develop machine learning models for data-driven solutions."
  },
  {
    "company_name": "ICURO",
    "url": "https://indeed.com/rc/clk?jk=7ff073880157fc9b&bb=iaeA_7VV77p9mQuXnUSmSs6a2CfDrl42eB1MmSgls97hhG1NqH9g_tiinaeSzwVB5eEbe7DBoA__qEP0OrL4UwUhZh0QHQv-HVSsvlOVlOWHzR3-5YvyWdjEAw2kQpkhE5WewkwFles%3D&xkcb=SoB467M3s42WqK20AJ0ZbzkdCdPP&fccid=b04472a1615bb565&cmp=ICURO&ti=Machine+Learning+Engineer&vjs=3",
    "matching_per": "91%",
    "job_title": "Machine Learning Engineer",
    "salary": "$150k",
    "job_other_details": "Full-time · Deep Learning/NLP",
    "benefits": "Stock options, health coverage",
    "full_description": "Build and optimize ML models for healthcare analytics."
  },
  {
    "company_name": "Avanza",
    "url": "https://indeed.com/rc/clk?jk=612cffc141139c9a&bb=WrizxPNZ3uQr-mAr35TGW1WTbxlKtuCFUY5htUdo56Fn9ZabcmdDebGXkuIG_NtQViT1T8yCdh9RsjvTDbUXonAyE4rP-x_U5NIGGIo1bhAus223lETj6-u6-zDpo6aD&xkcb=SoBA67M3s43LRQR7pR0BbzkdCdPP&fccid=540b61050e25d307&cmp=Avanza&ti=Ai+Architect&vjs=3",
    "matching_per": "94%",
    "job_title": "AI Architect",
    "salary": "$160k",
    "job_other_details": "Full-time · Remote · AI Solutions",
    "benefits": "Remote, paid leave, healthcare",
    "full_description": "Architect AI-driven platforms for enterprise clients."
  },
  {
    "company_name": "Prospance Inc",
    "url": "https://indeed.com/rc/clk?jk=3c9ac0bc6c57eb3d&bb=yigaxudHsy__X6BjmkGQgzAAiNu2Wuqs5IdU_hrY0g0oVPHmFyNNIJ_hxr6lM7HpNOkajRm5XYvpo-UZAOfEorKxXyFNcOMRR_KrDH8SFrqvqahvzeNQJRoPU3CVpysrJGV3MjM0F2TZwYaX8cr0GA%3D%3D&xkcb=SoAM67M3s43ybuwpR50PbzkdCdPP&fccid=d9ff0d7fd00093cd&cmp=Prospance-Inc&ti=Data+Engineer&vjs=3",
    "matching_per": "89%",
    "job_title": "Data Engineer",
    "salary": "$140k",
    "job_other_details": "Full-time · SQL/Python/AWS",
    "benefits": "Flexible hours, remote option",
    "full_description": "Manage data pipelines and optimize ETL processes."
  },
  {
    "company_name": "Incoexco",
    "url": "https://indeed.com/rc/clk?jk=af0557518da5105a&bb=21j5mTKEHNHVug5nN2icBpVZA9nuqBRzBC8nlebGiZqQhaCKE_t-bGuxUHKVys6Oaf9nXyakuDh-35J_qkY0RvvjbaUIE_NNN43ed0oJeIlrEqjqSKguPTxyxJ2YotGgzZOa2sElFWEHCdYDllKzxg%3D%3D&xkcb=SoAq67M3s5IjyOxMzh0BbzkdCdPP&fccid=1ee6ed83ce2d2156&cmp=Incoexco&ti=Python+Developer&vjs=3",
    "matching_per": "95%",
    "job_title": "Python Developer",
    "salary": "$135k",
    "job_other_details": "Full-time · Django/Flask",
    "benefits": "Health insurance, WFH",
    "full_description": "Develop APIs and backend systems in Python."
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




