from config import config_input
from utils import sheet_updater, helper
from utils.bypass.cloudflare import CloudflareBypasser
import logging, asyncio
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
import applications_submitter_module

# Shared logger for spider logs
logger = logging.getLogger("spider")

async def extract_full_details(context, urls, percentages):
    fixed_keys = [
        "company_name", "url", "matching_per", "job_title", "salary",
        "job_other_details", "benefits", "full_description"
    ]
    
    # Lists to hold different types of applications
    easy_applies = []
    cs_applies = []
    c_applies = []

    # Open a tab for navigating job detail pages
    tab2_page = await context.new_page()

    for p_index, url in enumerate(urls):
        # Make full Indeed job URL
        full_url = f"https://indeed.com{url}"
        
        # Initialize job data dictionary
        job_data = {key: "" for key in fixed_keys}
        job_data["url"] = full_url
        job_data["matching_per"] = percentages[p_index]

        # Check internet before proceeding
        if not await helper.check_internet():
            await helper.wait_until_internet_is_back(tab2_page)

        # Try navigating to job page (with retry)
        for attempt in range(2):
            try:
                await tab2_page.goto(full_url, wait_until="load")
                break
            except PlaywrightTimeoutError:
                if attempt < 1:
                    print(f"Attempt {attempt + 1} failed, retrying...")
                    await asyncio.sleep(2)
                else:
                    logger.warning(f"All attempts failed for {full_url}")
                    continue

        # Handle Cloudflare if it appears
        try:
            cf_bypasser = CloudflareBypasser(tab2_page)
            await cf_bypasser.detect_and_bypass()
        except Exception as e:
            logger.error(f"Captcha bypass failed: {e}")

        # Skip expired jobs
        if await tab2_page.query_selector(':has-text("This job has expired on Indeed")'):
            logger.info(f"Expired job skipped: {full_url}")
            continue

        # Simulate human-like browsing
        await helper.simulate_human_behavior(tab2_page)

        # Skip unwanted jobs
        try:
            content = await tab2_page.content()
            if any(keyword in content for keyword in config_input.AVIOD_JOBS):
                logger.info(f"Avoided job skipped: {full_url}")
                continue
        except Exception as e:
            logger.error(f"Error checking clearance: {e}")

        # Extract job details
        try:
            # Company name
            company_el = (await tab2_page.query_selector('[data-testid="company-name"]') or
                          await tab2_page.query_selector('[data-testid="inlineHeader-companyName"]'))
            if company_el:
                job_data["company_name"] = (await company_el.inner_text()).strip()
            else:
                logger.error(f"Failed to extract company name for {full_url}")
                continue

            # Job title
            title_el = await tab2_page.query_selector('[data-testid="jobsearch-JobInfoHeader-title"] span')
            if title_el:
                job_data["job_title"] = (await title_el.inner_text()).strip()
            else:
                logger.error(f"Failed to extract job title for {full_url}")
                continue

            # Salary
            salary_el = await tab2_page.query_selector('#salaryInfoAndJobType')
            if salary_el:
                job_data["salary"] = (await salary_el.inner_text()).strip()

            # Other details
            other_el = await tab2_page.query_selector('[data-testid="jobsearch-CompanyInfoContainer"]')
            if other_el:
                job_data["job_other_details"] = (await other_el.inner_text()).strip()

            # Benefits
            benefits_el = await tab2_page.query_selector('[data-testid="benefits-test"]')
            if benefits_el:
                job_data["benefits"] = (await benefits_el.inner_text()).strip()

            # Full description
            desc_el = await tab2_page.query_selector('#jobDescriptionText')
            if desc_el:
                job_data["full_description"] = (await desc_el.inner_text()).strip()
            else:
                logger.info(f"Job description missing for {full_url}")

        except Exception as e:
            logger.error(f"Error extracting job data for {full_url}: {str(e)}")
            continue

        # Classify the job type
        try:
            is_web_apply = bool(await tab2_page.query_selector(':has-text("Apply on company site")'))

            if job_data["company_name"] in getattr(config_input, 'confirmation_companies', []):
                c_applies.append(job_data)
                logger.info(f"Confirmation job: {job_data['company_name']}")
            elif is_web_apply:
                cs_applies.append(job_data)
                logger.info(f"Company site apply: {job_data['company_name']}")
            else:
                easy_applies.append(job_data)
                logger.info(f"Easy apply: {job_data['company_name']}")
        except Exception as e:
            logger.error(f"Unclassified job for {full_url}: {str(e)}")
            continue

    await tab2_page.close()

    # Save CS and confirmation jobs if required
    if config_input.SAVE_CS_AND_CONFIRMATION_APPLICATIONS:
        await sheet_updater.jobs_append_to_csv(cs_applies, c_applies)

    # Send easy applies for submission
    await applications_submitter_module.submitter(easy_applies=easy_applies)
