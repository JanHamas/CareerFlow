import asyncio, random, re, os
from datetime import datetime
from playwright_stealth import Stealth
from playwright.async_api import async_playwright
from config import config_input
from utils.bypass.cloudflare import CloudflareBypasser
from utils import accounts_loader, fingerprint_loader, proxies_loader, helper
from .job_details_scraper import extract_full_details
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import logging

logger = logging.getLogger("spider")  # use shared logger

# Load previews processed jobs id from txt file
processed_jobs_id = helper.load_processed_jobs_id()
# this are store companies name to avoid scrape many jobs of one company.
processed_new_company_jobs = []


async def _listing(context, job_page_url):
    """
    this is helper function for jobs_lister which scape titles, links and name of company but only pass to other function links we wrote complete logic of listing jobs from indeed and they are calling process_batch function. 
    """
    page = None
    try:
        # Create new page
        page = await context.new_page()
        
        # # Before performing critical actions, check internet
        if not await helper.check_internet():
            await helper.wait_until_internet_is_back(page)

        # Navigate to jobs page
        for attempt in range(5):  # 3 attempts: 0, 1, 2
            try:
                await page.goto(job_page_url, wait_until="load")
                break  # Success: exit loop
            except PlaywrightTimeoutError:
                if attempt < 2:  # first two attempts (0,1)
                    print(f"Attempt {attempt + 1} failed, retrying...")
                else:  # last attempt failed (attempt == 2)
                    logger.warning(f"All attempts failed for {job_page_url}")
                    await context.close()
                    await asyncio.sleep(random.randint(4,8))
                    return

        # Bypass cloudflare if appears
        try:
            cf_bypasser = CloudflareBypasser(page)
            await cf_bypasser.detect_and_bypass()
            await helper.handle_terms_cond_btn(page)
        except Exception as e:
            await context.close()
            logger.error(f"Captcha error: {e}")
            return
        
        # Temporary save extract data
        list_of_processed_jobs = []
        list_of_titles = []
        list_of_links = []
        pagination_number = 1

        while True:
            # # Before performing critical actions, check internet
            if not await helper.check_internet():
                await helper.wait_until_internet_is_back(page)
            
            # Bypass cloudflare if appears
            try:
                cf_bypasser = CloudflareBypasser(page)
                await cf_bypasser.detect_and_bypass()
            except Exception as e:
                logger.error(f"Captcha error: {e}")
                await context.close()
                return
            
            # Random wait for page load to sleep
            try:
                await page.wait_for_timeout(random.randint(3000, 10000))
            except Exception as e:
                logger.warning("Page not load successfully: {e}")
           
            # random sleep, simulate human acting on page.
            await asyncio.sleep(config_input.RANDOM_SLEEP)
            await helper.simulate_human_behavior(page)

            # titles, companies, links are html elements for extract information
            try:
                titles_task = page.query_selector_all(".jobTitle")
                companies_task = page.query_selector_all("[data-testid='company-name']")
                links_task = page.query_selector_all("tr td a")
                titles, companies, links = await asyncio.gather(titles_task, companies_task, links_task)
            except Exception as e:
                logger.error(f"Selector issue: {e}")
                break

            # Iterate all html elements for geting data and process further
            for title, company, link in zip(titles, companies, links):
                link = await link.get_attribute("href")
                # if link not found then rejump to loop
                if not link:
                    logger.warning(f"link not extracted from urls.")
                    continue

                # append processd jobs list to save in test file to avoid duplicate.
                # extract job_id from link
                list_of_processed_jobs.append(link)
                job_id = await helper.get_job_id(link)

                # if job id not extract then again jump to loop.
                if not job_id:
                    logger.warning(f"Job id not extracted from urls : {link}")
                    continue
                
                # get text from title, company name
                title_text = await title.inner_text()
                company_name = await company.inner_text()

                # Count compnay name which are processed for avoid to scrape one company many jobs.
                count = processed_new_company_jobs.count(company_name)

                # Skip if job already processed, if company in list of ignore company
                # if company limited jobs scrape
                if (
                    count > config_input.PER_COMPANY_JOBS
                    or job_id in processed_jobs_id
                    or company_name in config_input.ignore_companies
                ):
                    continue

                # Append job id to processed jobs id
                processed_jobs_id.add(job_id)

                # Append company name which processed, titles, links. 
                processed_new_company_jobs.append(company_name)
                list_of_titles.append(title_text)
                list_of_links.append(link)

                # print log when five jobs collected.
                if len(list_of_titles) % 5 == 0:
                    logger.info(f"Collected {len(list_of_titles)} jobs...")

                # if length of titles become >= length of process batch size then call process_batch function.
                if len(list_of_titles) >= config_input.PROCESS_BATCH_SIZE:
                    logger.info("Processing batch...")
                    await process_batch(context, list_of_titles, list_of_links)
                    # clear list for collecting new jobs
                    list_of_titles.clear()
                    list_of_links.clear()
                    # Append processed jobs to test file and then clear
                    await helper.update_processed_jobs(list_of_processed_jobs)
                    list_of_processed_jobs.clear()
            
            # Click on pagination button.
            try:
                await page.wait_for_selector(f"[data-testid='pagination-page-{pagination_number + 1}']", state="visible")
                await page.click(f"[data-testid='pagination-page-{pagination_number + 1}']")
                pagination_number += 1
            except Exception as e:
                filename = f"screenshot_{pagination_number}.png"
                file_path = os.path.join(config_input.DEBUGGING_SCREENSHOTS_PATH, filename)
                await page.screenshot(path=file_path, full_page=True)
                logger.info(f"No more pages. Screenshot saved: {file_path}")
                logger.warning(f"Failed to click page {pagination_number + 1}: {e}")
                break
        # process those jobs which remained after pagniation error.
        if list_of_titles:
            await process_batch(context, list_of_titles, list_of_links)
            await helper.update_processed_jobs(list_of_processed_jobs)
    except Exception as e:
        logger.exception(f"Error in _listing: {e}")
    finally:
        try:
            if page:
                await page.close()
            await context.close()
            logger.debug("Context closed")
        except Exception as e:
            logger.error(f"Context close issue: {e}")


async def process_batch(context, list_of_titles, list_of_links):
    # prompt for getting jobs matching responses.
    prompt = f"""{config_input.AI_PROMPT}\n
{config_input.RESUME}\n
Jobs Titles:
{list_of_titles}
    """
    # show promt if we want.
    if config_input.show_ai_prompt_for_getting_matching_percentage:
        logger.info(f"Prompt for ai to getting jobs matching percentaga. \n {prompt}")
    try:
        
        # Get jobs matching response from ai.
        model_response = await helper.get_match_percentage(prompt)

        if config_input.show_ai_response_for_getting_matching_percentage:
            logger.info(f"Response of ai for matching percentage of jobs. \n {model_response}")

        # Only extract number and then convert list of integer
        matching_percentages = re.findall(r'\b\d+\b', model_response)
        matching_percentages = list(map(int, matching_percentages))

        # create list for those jobs which we want to processed further.
        links_list = []
        percentages = []
        for percentage, link in zip(matching_percentages, list_of_links):
            if percentage >= config_input.MATCHING_PERCENTAGE:
                links_list.append(link)
                percentages.append(percentage)
        
        # if jobs list are appended then processed further.
        if links_list:
            await extract_full_details(context, links_list, percentages)

    except Exception as e:
        logger.exception(f"Batch processing failed: {e}")
        await context.close()

async def jobs_lister(all_urls):
    proxies = await proxies_loader.load_proxies()
    accounts = await accounts_loader.load_accounts()

    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=config_input.headless)

        semaphore = asyncio.Semaphore(config_input.MAX_CONTEXTS)  # 5 limit concurrent contexts

        async def worker(job_page_url, index):
            async with semaphore:
                try:
                    context = await browser.new_context(proxy=proxies[index % len(proxies)])
                    script = await fingerprint_loader.load_fingerprint(index)
                    await context.add_init_script(script=script)

                    try:
                        await context.add_cookies(accounts[index % len(accounts)])
                    except:
                        await context.add_cookies(random.choice(accounts))

                    await _listing(context, job_page_url)
                except Exception as e:
                    logger.exception(f"Context/Listing failed for {job_page_url}: {e}")

        tasks = []
        for index, url in enumerate(all_urls):
            tasks.append(asyncio.create_task(worker(url, index)))

        await asyncio.gather(*tasks)

        await browser.close()
