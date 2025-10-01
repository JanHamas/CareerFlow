import asyncio, random, re, os
from playwright_stealth import Stealth
from playwright.async_api import async_playwright
from datetime import datetime
from config import config_input
from utils.bypass.cloudflare import CloudflareBypasser
from utils import accounts_loader, fingerprint_loader, proxies_loader, helper
from .job_details_scraper import extract_full_details
import logging
from typing import List

# get logger file for saving spider logs.
logger = logging.getLogger("spider")  # use shared logger


""" This function are submit application."""
async def submitter(easy_applies: List[List[str]]) -> None:

    accounts = await accounts_loader.load_accounts(config_input.INDEED_ACCOUNT_DIR)  # list of accounts

    async with Stealth().use_async(async_playwright()) as p:
        
        # create instance of browser with mode headed/headless
        browser = await p.chromium.launch(headless=config_input.headless)

        try:
            context = await browser.new_context()
            try:
                await context.add_cookies(accounts[len(accounts)])
            except:
                await context.add_cookies(random.choice(accounts))

            await _submiting_logic(context, easy_applies)

        except Exception as e:
            logger.exception(f"Context/Listing failed for {easy_applies}: {e}")


        await browser.close()


async def _submiting_logic():
     pass
