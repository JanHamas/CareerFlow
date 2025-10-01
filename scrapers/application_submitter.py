import asyncio, random, re, os
from playwright_stealth import Stealth
from playwright.async_api import async_playwright
from datetime import datetime
from config import config_input
from utils.bypass.cloudflare import CloudflareBypasser
from utils import accounts_loader, fingerprint_loader, proxies_loader, helper
from .job_details_scraper import extract_full_details
import logging


# get logger file for saving spider logs.
logger = logging.getLogger("spider")  # use shared logger



""" This function are submit application."""
async def submitter():

    proxies = await proxies_loader.load_proxies()     # list of proxies
    accounts = await accounts_loader.load_accounts()  # list of accounts


    async with Stealth().use_async(async_playwright()) as p:
        
        # create instance of browser with mode headed/headless
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
