from config import config_input
from utils import sheet_uploader
from utils.bypass.cloudflare import CloudflareBypasser
from utils import helper
import logging

# get logger file for saving spider logs.
logger = logging.getLogger("spider")  # use shared logger


""" This function are extracing all info about jobs and classifing and push for sumbiting processing."""
async def extract_full_details(context, urls, percentages):

    fixed_keys = [  "company_name", "url",    "matching_per",
                    "job_title",    "salary", "job_other_details",
                    "benefits",      "full_description"
                    ]


    easy_applies = []
    cs_applies = []
    c_applies = []
    unclassified_jobs = []

    tab2_page = await context.new_page()
    
        
    for p_index, url in enumerate(urls):
        # Before performing critical actions, check internet
        if not await helper.check_internet():
            await helper.wait_until_internet_is_back(tab2_page)
        
        full_url = f"https://indeed.com{url}"

        # Navigating to page to extract complete info
        try:
            await tab2_page.goto(full_url, wait_until="load")
        except Exception as e:
            try:
                await tab2_page.reload()
                await tab2_page.goto(full_url, wait_until="load")
            except Exception as e:
                logger.info(f"Page not loaded after two tries: {e}")
                continue
        
        # Simulate human behavior
        await helper.simulate_human_behavior(tab2_page)

        # Bypass if cloudflare appear
        try:
            cf_bypasser = CloudflareBypasser(tab2_page)
            await cf_bypasser.detect_and_bypass()
        except Exception as e:
            logger.error(f"Captcha bypass failed: {e}")

    
        job_data = {key: "" for key in fixed_keys}
        job_data.update({
            "url": full_url,
            "matching_per": percentages[p_index]
        })

        try:
            content = await tab2_page.content()
            if any(keyword in content for keyword in config_input.AVIOD_JOBS):
                logger.info(f"Clearance-related job skipped: {full_url}")
                continue
        except Exception as e:
            logger.error(f"Error checking clearance: {e}")

        try:
            company_el = (await tab2_page.query_selector('[data-testid="company-name"]') or 
                          await tab2_page.query_selector('[data-testid="inlineHeader-companyName"]'))
            if company_el:
                job_data["company_name"] = (await company_el.inner_text()).strip()
            else:
                logger.error(f"Failed to extract company name")
                continue

            title_el = await tab2_page.query_selector('[data-testid="jobsearch-JobInfoHeader-title"] span')
            if title_el:
                job_data["job_title"] = (await title_el.inner_text()).strip()
            else:
                logger.error(f"Failed to extract job title")
                continue

            salary_el = await tab2_page.query_selector('#salaryInfoAndJobType')
            if salary_el:
                job_data["salary"] = (await salary_el.inner_text()).strip()
            else:
                logger.info(f"Salary missing")

            try:
                el = await tab2_page.query_selector('[data-testid="jobsearch-CompanyInfoContainer"]')
                if el:
                    job_data["job_other_details"] = (await el.inner_text()).strip()
            except:
                logger.info(f"Job other details missing")

            benefits_el = await tab2_page.query_selector('[data-testid="benefits-test"]')
            if benefits_el:
                job_data["benefits"] = (await benefits_el.inner_text()).strip()
            else:
                logger.info(f"Benefits missing")

            desc_el = await tab2_page.query_selector('#jobDescriptionText')
            if desc_el:
                job_data["full_description"] = (await desc_el.inner_text()).strip()
            else:
                logger.info(f"[ERROR] Job description missing")

        except Exception as e:
            logger.error(f"Partial data extraction for {full_url}: {str(e)}")

        row = [job_data[key] for key in fixed_keys]

        try:
            if await tab2_page.query_selector(':has-text("This job has expired on Indeed")'):
                logger.info(f"Expired job: {job_data['company_name']}")
                continue

            is_web_apply = bool(await tab2_page.query_selector(':has-text("Apply on company site")'))

            if job_data["company_name"] in getattr(config_input, 'confirmation_companies', []):
                c_applies.append(row)
                logger.info(f"Confirmation job: {job_data['company_name']}")
            elif is_web_apply:
                cs_applies.append(row)
                logger.info(f"Company site apply: {job_data ['company_name']}")
            else:
                easy_applies.append(row)
                logger.info(f"Easy apply: {job_data['company_name']}")

        except Exception as e:
            unclassified_jobs.append(full_url)
            logger.error(f"[ERROR] Unclassified job: {full_url} - {str(e)}")

    await tab2_page.close()
    await sheet_uploader.jobs_append_to_csv(easy_applies, cs_applies, c_applies)
