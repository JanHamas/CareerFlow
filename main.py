import time
import requests

def check_internet():
    test_sites = [
        "https://1.1.1.1",
        "https://www.cloudflare.com",
        "https://example.com",
        "https://www.bing.com"
    ]
    
    for site in test_sites:
        try:
            response = requests.get(site, timeout=10)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass    
    return False

# Wait until internet is available
while not check_internet():
    print("Check your internet connection...")
    time.sleep(5)

from scrapers.job_listings_scraper import jobs_lister
import asyncio, time
from utils import helper, sheet_updater
from config import config_input
from utils.logger_setup import setup_logger

if __name__ == "__main__":
                
    logger = setup_logger()

    try:
        logger.info("🚀 Project Acquirer AI started")

        # Prevent screen to sleep
        sb = helper.SleepBlocker()
        sb.prevent_sleep()
        
        # Create first new workbook with three sheets for saving scraper result
        helper.create_csv_files(config_input.CSV_FILES)
        logger.info("✅ Fresh CSV files created")

        # Clean the processed saved jobs file
        helper.clean_processed_jobs_file()
        logger.info("🧹 Processed jobs file cleaned")

        # Create a debugging folder
        folder_path = "debugging_screenshots"
        helper.create_debugging_screenshots_folder(folder_path)
        logger.info("📁 Debugging folder ready")

        # Jobs lister main function
        asyncio.run(jobs_lister(config_input.jobs_listed_pages_urls))
        
        # Send debugging pictures + logs
        helper.send_debugging_screenshots_and_spider_log_email()
        logger.info("📤 Debugging screenshots and spider.logs email sent")

    except Exception:
        logger.exception("❌ Error in main.py")
    finally:
        sb.allow_sleep()
        logger.info("🛑 Scraper finished, sleep mode re-enabled")
