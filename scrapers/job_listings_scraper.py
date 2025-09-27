import asyncio, random, re, os
from playwright_stealth import Stealth
from playwright.async_api import async_playwright
from datetime import datetime
from config import config_input
from utils.bypass.cloudflare import CloudflareBypasser
from utils import accounts_loader, fingerprint_loader, proxies_loader, helper
from .job_details_scraper import extract_full_details
import logging


# get the logger file for saving logs.
logger = logging.getLogger("spider") 

# Load all jobsd ids from previews processd jobs for avoid duplicate and create a new list for saving comapnies for avoid listing many jobs of one companies.
processed_jobs_id = helper.load_processed_jobs_id()
processed_new_company_jobs = []



""" This function listing and push jobs for furthers processing."""
async def _listing(context, job_page_url):
    page = None
    try:
        # Create new page
        page = await context.new_page()

        # Before performing critical actions, check internet
        if not await helper.check_internet():
            await helper.wait_until_internet_is_back(page)
        
        # Navigate to jobs page
        for attempt in range(3):
            try:
                await page.goto(job_page_url, wait_until="load")
                await helper.handle_terms_cond_btn(page)
                break  # Success: exit loop
            except TimeoutError:
                print(f"Attempt {attempt + 1} failed, retrying...")

                # Format datetime to make it filename-safe
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"screenshot_{timestamp}.png"
                file_path = os.path.join(config_input.DEBUGGING_SCREENSHOTS_PATH, filename)

                # Take a full-page screenshot
                await page.screenshot(path=file_path, full_page=True)

                # Wait before retrying
                await asyncio.sleep(2)
        
        # Bypass cloudflare if appears
        try:
            cf_bypasser = CloudflareBypasser(page)
            await cf_bypasser.detect_and_bypass()
        except Exception as e:
            logger.error(f"Captcha error: {e}")
        

        # Temporary save extract data
        list_of_processed_jobs = []
        list_of_titles = []
        list_of_links = []
        pagination_number = 1

        while True:
            # Before performing critical actions, check internet
            if not await helper.check_internet():
                await helper.wait_until_internet_is_back(page)


            # wait rondomly to load page.
            try:
                await page.wait_for_timeout(random.randint(3000, 10000))
            except Exception as e:
                pass

            # wait randomly to make simulate human behavior.
            await asyncio.sleep(config_input.RANDOM_SLEEP)
            
            # function that simulate human behavior on page like click, scrolling and so on.
            await helper.simulate_human_behavior(page)

            # Selector to select titles, companies, links of jobs
            try:
                titles_task = page.query_selector_all(".jobTitle")
                companies_task = page.query_selector_all("[data-testid='company-name']")
                links_task = page.query_selector_all("tr td a")
                titles, companies, links = await asyncio.gather(titles_task, companies_task, links_task)

            except Exception as e:
                logger.error(f"Selector issue: {e}")
                break

            # Main loop that check jobs and push for futher process if they meet with criterias
            for title, company, link in zip(titles, companies, links):
                link = await link.get_attribute("href")
                
                if not link:
                    continue

                # Append processed to txt file and get jobs id.
                list_of_processed_jobs.append(link)
                job_id = await helper.get_job_id(link)
                if not job_id:
                    logger.warning("Failed to extract job id!")
                    continue
                
                # Extract title and company name in text format.
                title_text = await title.inner_text()
                company_name = await company.inner_text()

                # Count the company how many jobs are listed of there.
                count = processed_new_company_jobs.count(company_name)
                
                # Skip jobs if they meet with below critera
                if (
                    count > config_input.PER_COMPANY_JOBS
                    or job_id in processed_jobs_id
                    or company_name in config_input.ignore_companies
                ):
                    continue

                # Append jobs ids and companies name for avoid duplicate.
                processed_jobs_id.add(job_id)
                processed_new_company_jobs.append(company_name)

                # Append titles and jobs links for further processing.
                list_of_titles.append(title_text)
                list_of_links.append(link)

                # Pring and save logs when collect clear 5 jobs
                if len(list_of_titles) % 5 == 0:
                    logger.info(f"Collected {len(list_of_titles)} jobs...")

                # if list of title => batch size then processd and submit application
                if len(list_of_titles) >= config_input.PROCESS_BATCH_SIZE:
                    logger.info("Processing batch...")
                    await process_batch(context, list_of_titles, list_of_links)
                    list_of_titles.clear()
                    list_of_links.clear()
                    # saving the processed jobs links in text file and clear list.
                    await helper.update_processed_jobs_links(list_of_processed_jobs)
                    list_of_processed_jobs.clear()

            # Click on pagination
            try:
                button_locator = page.locator(f"[data-testid='pagination-page-{pagination_number + 1}']")
                if await button_locator.is_visible(timeout=10000):
                    await button_locator.click(timeout=10000)
                    pagination_number += 1
                else:
                    filename = f"screenshot_{pagination_number}.png"
                    file_path = os.path.join(config_input.DEBUGGING_SCREENSHOTS_PATH, filename)
                    await page.screenshot(path=file_path, full_page=True)
                    logger.info(f"No more pages. Screenshot saved: {file_path}")
                    break
            except Exception as e:
                logger.warning(f"Failed to click page {pagination_number + 1}: {e}")
                break
        
        # if list of titles contain titles push that for furthers process.
        if list_of_titles:
            await process_batch(context, list_of_titles, list_of_links)
            # saving the processed jobs links in text file and clear list
            await helper.update_processed_jobs_links(list_of_processed_jobs)
            list_of_processed_jobs.clear()
    
    except Exception:
        logger.exception("Error in _listing")
    finally:
        try:
            if page:
                await page.close()
            await context.close()
            logger.debug("Context closed")
        except Exception as e:
            logger.error(f"Context close issue: {e}")


""" This function process batch with AI and push the matched jobs for submits application."""
async def process_batch(context, list_of_titles, list_of_links):

# Prompt var contian ai_prompt, resume, and extracted jobs titles for get matching matching percengates.
    prompt = f"""{config_input.AI_PROMPT}\n
{config_input.RESUME}\n
Jobs Titles:
{list_of_titles}


    """
    try:
        # Get the matching percentage of each jobs base with provided resume/
        model_response = await helper.get_match_percentage(prompt)
        matching_percentages = re.findall(r'\b\d+\b', model_response)
        matching_percentages = list(map(int, matching_percentages))

        # Save those jobs links which are matching with our criterias
        links_list = []
        percentages = []

        # Extract only those jobs links which matching with required percentage
        for percentage, link in zip(matching_percentages, list_of_links):
            if percentage >= config_input.MATCHING_PERCENTAGE:
                links_list.append(link)
                percentages.append(percentage)

        # if jobs extract then submit application to that jobs
        if links_list:
            await extract_full_details(context, links_list, percentages)

    except Exception:
        logger.exception("Batch processing failed")
        await context.close()


""" This function are calling listing helper function many time for listing jobs. with seperated things, like: proxies, fingerprint so on."""
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
