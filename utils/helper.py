import urllib.parse, time
import traceback, os, shutil, csv, io, re
from dotenv import load_dotenv
from playwright.async_api import Page
import google.generativeai as genai
import asyncio, random , aiofiles
import platform, subprocess, ctypes
from urllib.parse import urlparse, parse_qs
import smtplib
from email.message import EmailMessage
import mimetypes
from config import config_input
from groq import Groq
import logging, aiohttp, requests
from google.api_core.exceptions import ResourceExhausted
from datetime import datetime
from utils import sheet_uploader
from playwright.async_api import Locator
import aioconsole

# Logger
logger = logging.getLogger("spider")

# Load environment variables
load_dotenv()

# Create CSV file for simultinouly saveing scraping data
def create_csv_files(file_names):
    """Create empty CSV files inside output/ directory."""
    os.makedirs("output", exist_ok=True)
    for name in file_names:
        path = os.path.join("output", f"{name}")
        with open(path, mode="w", newline='', encoding="utf-8"):
            pass
        logger.info(f"Created fresh file: {path}")

# Load jobs id from previews 1,2,3 day ago processed jobs for avoid duplicate
def load_processed_jobs_id(filename=config_input.PROCESSED_JOBS_FILE_PATH):
    """Load job IDs from previously processed jobs file."""
    try:
        jobs_id = set()
        with open(filename, 'r') as f:
            for url in f:
                parsed_url = urlparse(url.strip())
                query_params = parse_qs(parsed_url.query)
                job_id = query_params.get("jk", [None])[0]
                if job_id:
                    jobs_id.add(job_id)
        logger.info(f"Loaded {len(jobs_id)} job IDs from {filename}")
        return jobs_id
    except Exception:
        logger.exception("Error loading job IDs")
        return set()

# Create a logs and debugging_screenshot folder for saveing spider and screenshots
def create_debugging_screenshots_folder(folder_path):
    """Recreate debugging/log folders from scratch."""
    try:
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            os.mkdir(folder_path)
            logger.info(f"Created new folder: {folder_path}")
    except Exception:
        logger.exception(f"Failed to create folder {folder_path}")

async def get_job_id(url):
    """Extract job_id from a given URL."""
    try:
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        return query_params.get("jk", [None])[0]
    except Exception:
        logger.exception("Error extracting job_id")
        return None

async def update_processed_jobs(links):
    """Append new processed jobs to the file."""
    try:
        with open(config_input.PROCESSED_JOBS_FILE_PATH, "a") as f:
            for link in links:
                f.write(f"{link}\n")
            f.flush()
        logger.info(f"Updated processed jobs with {len(links)} new links")
    except Exception:
        logger.exception("Failed to update processed jobs")

# AI matching function
genai.configure(api_key=os.getenv("GEMIMI_API_KEY"))
async def get_match_percentage_from_gemini(prompt: str):
    """Get match percentage using Gemini."""
    try:
        model = genai.GenerativeModel(config_input.gemini_model_version)
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text.strip()
    except Exception:
        logger.exception("Error in get_match_percentage")
        return None

async def get_match_percentage_from_groq(prompt):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    messages = [{"role": "user", "content": prompt}]
    
    try:
        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0,
                max_tokens=1024,
                top_p=1,
                stream=False
            )
        )

        response_text = completion.choices[0].message.content.strip()
        return response_text

    except Exception as e:
        print("\nError:", e)
        print(traceback.format_exc())
        return None

async def simulate_human_behavior(page: Page):
    """Simulate faster human-like behavior on a page."""

    # Simulate scrolling (like someone casually reading)
    for _ in range(random.randint(1, 2)):  # fewer scrolls
        scroll_amount = random.randint(100, 200)  # smaller scroll amount
        await page.mouse.wheel(0, scroll_amount)
        await asyncio.sleep(random.uniform(0.2, 0.5))  # shorter wait between scrolls

    # Move mouse quickly (simulate hand movement)
    await page.mouse.move(
        random.randint(0, 800),
        random.randint(0, 600),
        steps=random.randint(5, 10)  # fewer steps for faster movement
    )

    # Scroll to bottom like a user might do
    await smooth_scroll_to_page_bottom(page=page)

class SleepBlocker:
    """Prevent system from sleeping during scraping."""

    def __init__(self):
        self.platform = platform.system()
        self.proc = None

    def prevent_sleep(self):
        try:
            if self.platform == "Windows":
                ES_CONTINUOUS = 0x80000000
                ES_SYSTEM_REQUIRED = 0x00000001
                ES_DISPLAY_REQUIRED = 0x00000002
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
                )
            elif self.platform == "Darwin":
                self.proc = subprocess.Popen(["caffeinate"])
            elif self.platform == "Linux":
                self.proc = subprocess.Popen(["bash", "-c", "while true; do sleep 60; done"])
            else:
                logger.warning("Unsupported OS for sleep prevention")
        except Exception:
            logger.exception("Failed to prevent sleep")

    def allow_sleep(self):
        try:
            if self.platform == "Windows":
                ES_CONTINUOUS = 0x80000000
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            elif self.platform in ["Darwin", "Linux"]:
                if self.proc:
                    self.proc.terminate()
                    self.proc = None
            else:
                logger.warning("Unsupported OS for allowing sleep")
        except Exception:
            logger.exception("Failed to allow sleep")

def clean_processed_jobs_file():
    """Keep only the last N lines in processed_jobs.txt."""
    try:
        with open(config_input.PROCESSED_JOBS_FILE_PATH, 'r') as f:
            urls = f.readlines()
        last_urls = urls[-8000:]
        with open(config_input.PROCESSED_JOBS_FILE_PATH, 'w') as f:
            f.writelines(last_urls)
        logger.info(f"Trimmed processed jobs file to last {len(last_urls)} entries")
    except Exception:
        logger.exception("Failed to clean processed jobs file")

def sort_csv_files_by_column(filenames=config_input.CSV_FILES, sort_column_index=4):
    """Sort CSV files by a column in descending order."""
    encodings_to_try = ['utf-8', 'latin1', 'cp1252', 'utf-8-sig']

    for filename in filenames:
        filename = f"output/{filename}"
        rows, chosen_encoding = None, None

        for encoding in encodings_to_try:
            try:
                with open(filename, 'r', newline='', encoding=encoding) as f:
                    rows = list(csv.reader(f))
                chosen_encoding = encoding
                logger.info(f"Read {filename} with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
            except Exception:
                logger.warning(f"Error reading {filename} with {encoding}", exc_info=True)

        if not rows:
            logger.warning(f"Could not read {filename} or file is empty. Skipping.")
            continue

        try:
            int(rows[0][sort_column_index])
            has_header = False
        except (ValueError, IndexError):
            has_header = True

        header = rows[0] if has_header else None
        data = rows[1:] if has_header else rows

        try:
            data.sort(key=lambda row: int(row[sort_column_index]), reverse=True)
        except Exception:
            logger.warning(f"Sorting failed for {filename}, saving unsorted.", exc_info=True)

        try:
            with open(filename, 'w', newline='', encoding=chosen_encoding) as f:
                writer = csv.writer(f)
                if header:
                    writer.writerow(header)
                writer.writerows(data)
            logger.info(f"Sorted and saved {filename}")
        except Exception:
            logger.exception(f"Failed to write sorted data for {filename}")

def send_debugging_screenshots_and_spider_log_email(folder_path="debugging_screenshots", log_file="logs/spider.log"):
    """Send debugging screenshots and spider.log via email."""
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    recipient = os.getenv("EMAIL_RECIPIENT")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not all([sender, password, recipient, smtp_server]):
        logger.error("Missing one or more required .env values for email")
        return

    msg = EmailMessage()
    msg["Subject"] = "🪲 Debugging Files"
    msg["From"] = sender
    msg["To"] = recipient
    msg.set_content("Attached are the latest debugging screenshots and logs.")

    attached = 0

    # Attach screenshots
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if os.path.isfile(filepath) and filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                ctype, encoding = mimetypes.guess_type(filepath)
                if ctype is None or encoding is not None:
                    ctype = 'application/octet-stream'
                maintype, subtype = ctype.split('/', 1)
                with open(filepath, 'rb') as f:
                    msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=filename)
                    attached += 1
    else:
        logger.warning(f"Folder '{folder_path}' not found.")

    # Attach spider.log
    if os.path.exists(log_file):
        with open(log_file, "rb") as f:
            msg.add_attachment(f.read(), maintype="text", subtype="plain", filename=os.path.basename(log_file))
            attached += 1
    else:
        logger.warning(f"Log file '{log_file}' not found.")

    if attached == 0:
        logger.warning("No files found to attach.")
        return

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        logger.info(f"Email sent to {recipient} with {attached} attachments")
    except Exception:
        logger.exception("Failed to send debugging email")

async def handle_terms_cond_btn(page):
    try:
        # Wait for the Accept Terms button using an exact selector
        await page.wait_for_selector('button[data-gnav-element-name="AcceptButton"]', timeout=5000)
        accept_button = await page.query_selector('button[data-gnav-element-name="AcceptButton"]')

        if accept_button:
            # Scroll into view just in case
            await accept_button.scroll_into_view_if_needed()

            # Get the button's bounding box to calculate where to click
            box = await accept_button.bounding_box()
            if box:
                # Move the mouse to the center of the button and click
                x = box["x"] + box["width"] / 2
                y = box["y"] + box["height"] / 2

                await page.mouse.move(x, y)
                await page.mouse.down()
                await asyncio.sleep(0.1)  # simulate slight press delay
                await page.mouse.up()

                logger.info("Successfully clicked Accept Terms using real mouse events.")
                await asyncio.sleep(3)  # Wait for modal to close
            else:
                logger.warning("Could not get bounding box for Accept Terms button.")
        else:
            logger.warning("Accept Terms button not found.")
    except Exception as e:
        logger.error(f"NotError/found clicking Accept Terms button.")

async def get_match_percentage(prompt:str):
    model_response = None
    try:
        model_response = await get_match_percentage_from_gemini(prompt)
        logger.info(f"Gemini response: {model_response}")
    except ResourceExhausted as e:
        logger.error("Gemini quota exceeded, falling back to Groq...")
    except Exception as e:
        logger.error(f"Error from Gemini:")

    # Fallback if Gemini fails or returns None
    if not model_response:
        try:
            model_response = await get_match_percentage_from_groq(prompt)
            logger.info(f"Groq response: {model_response}")
        except Exception as e:
            logger.error(f"Error from Groq:")
            model_response = None  # Optional: keep as None for later handling

    return model_response

# Async function to check internet connectivity
async def check_internet():
    test_sites = [
        "https://1.1.1.1",
        "https://www.cloudflare.com",
        "https://example.com",
        "https://www.bing.com"
    ]
    
    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for site in test_sites:
            try:
                async with session.get(site) as response:
                    if response.status == 200:
                        return True
            except aiohttp.ClientError:
                pass  # Ignore failed site and try next

    return False

# Function to wait until internet is back and optionally refresh the page
async def wait_until_internet_is_back(page:Page):
    print("❌ Internet connection lost. Waiting to reconnect...")
    while not await check_internet():
        await asyncio.sleep(10)
    print("Internet reconnected.")
    await page.reload()


async def click_continue_button(page: Page, btn_name: str, step:str, job: dict):
    """Click visible 'Continue' button (iframe or main page)."""
    await simulate_human_behavior(page=page)
   
    # if btn_name are submit application button then there will be not continue btn only two btn will be aviable the review your application or submit your application
    if btn_name.lower() == "submit application button":
        # if review your application button page not found then call submission
        try:
            await upload_coverletter_and_submit_application(page, step=step, job=job)
        except Exception as e:
            logger.error(f"Failed to click on Review or Continue button: {e}")
            return False
    # if btn_name was not submit your application then there must be continue btn
    else:
        try:
            found = False
            # 1️⃣ Search inside iframes
            for frame in page.frames:
                if any(k in frame.url for k in ["indeedapply", "apply"]):
                    try:
                        buttons = frame.locator("button:has-text('Continue')")
                        for i in range(await buttons.count()):
                            btn = buttons.nth(i)
                            if await btn.is_visible():
                                await btn.click()
                                logger.info(f"Clicked {btn_name} 'Continue' inside iframe (#{i}).")
                                found = True
                                break
                        if found:
                            break
                    except Exception as e:
                        logger.warning(f"Error accessing iframe: {e}")

            # 2️⃣ Search on main page if not found
            if not found:
                buttons = page.locator("button:has-text('Continue')")
                count = await buttons.count()
                for i in range(count):
                    btn = buttons.nth(i)
                    if await btn.is_visible():
                        await btn.scroll_into_view_if_needed()
                        await btn.click()
                        logger.info(f"Clicked 'Continue' button on main page (#{i}).")
                        found = True
                        break
            # 3️⃣ If still not found, check for 'Review your application' or submit
            if not found:
                logger.warning("No visible or clickable 'Continue' button found. try review your application one.")
                # Click on review you application button if appear.
                current_url = page.url
                if "review-module" not in page.url:
                    try:
                        btn_name = "Review your application"
                        review_btn = page.get_by_text("Review your application", exact=True)
                        if await review_btn.is_visible():
                            await review_btn.click()
                            logger.info("Clicked on 'Review your application' button.")
                            await wait_for_page_to_load(page=page, btn_name=btn_name, current_url=current_url)
                            found = True
                    except Exception:
                        logger.warning("Error while trying to click 'Review your application' button.")
                        return False
                    # if review your application button page not found then call submission
                    if "review-module" in page.url:
                        try:
                            await upload_coverletter_and_submit_application(page, step=step, job=job)
                            found = True
                        except Exception as e:
                            logger.error(f"Failed to click on Review or Continue button: {e}")
                            return False
                    
            return found # When found became True in continue section then we have to return true

        except Exception as e:
            logger.error(f"Unexpected error while clicking 'Continue': {e}")
            return False


async def upload_coverletter_and_submit_application(page: Page, step: int, job: dict):
    """
    Uploads a cover letter and submits the application.
    """
    logger.info("Application submission page found. Attempting submission...")
    await smooth_scroll_to_page_bottom(page=page)
    
    # Upload cover letter
    await update_cover_letter(page, job)

    # Try to click on submit button
    try:
        btn_name = "Submit your application"
        current_url = page.url
        submit_btn = page.get_by_text(btn_name, exact=True)
        if await submit_btn.is_visible():
            await submit_btn.click()
            logger.info(f"Application submitted successfully in step {step}.")
            await wait_for_page_to_load(page=page, btn_name=btn_name, current_url=current_url)
            # Save job info
            await append_job_data_in_csv(file_path=config_input.easy_applies_sheet_file_path,data_dict=job)
            return False # navigating to next jobs
        else:
            logger.warning("No visible 'Submit your application' button found.")
    except Exception as e:
        logger.warning(f"Error clicking on submit button: {e}")
    
    
    # Return False to indicate end of current job
    return False


# this one function are gonna save info about submitted jobs
async def append_job_data_in_csv(file_path, data_dict):
    # get current date
    now = datetime.now()
    # format current time
    current_time_formatted_ampm = now.strftime("%I:%M:%S %p")
    # append data_dict with current time
    data_dict["current_time"] = current_time_formatted_ampm
    # Create an in-memory buffer
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(data_dict.values())  # write only the values
    # Write asynchronously to file
    try:
        async with aiofiles.open(file_path, mode='a', newline='') as f:
            await f.write(buffer.getvalue())
            logger.info("Job all informatios are append to CSV.")
            return False  # false returned for navigating to next job to submit.
    except Exception as e:
        logger.warning(f"Error to append jobs data to csv: {e}")
        return False
    return False

    
# === below are some best function for handle common quries in jobs application ===
async def handle_cover_letter(page: Page, question_ele:Locator, question:str, index:int, skip_common_queries: list):
    try:
        logger.info("Cover letter question are found and puting...")
        # Find the input element for file upload
        input_file = await question_ele.query_selector("xpath=.//input[@data-testid='fileUploadInput']")
        
        if not input_file:
            logger.warning("File upload input not found.")
            return False

        # Upload the cover letter file
        resume_path = config_input.cover_letter_path
        await input_file.set_input_files(resume_path)

        logger.info("Cover letter uploaded successfully.")
        skip_common_queries.append(index)
        return True

    except Exception as e:
        logger.error(f"Error uploading cover letter: {e}")
        return False

# This function handles country-related questions.
async def handle_country_selection(page: Page, question_ele: Locator, question: str, index: int, skip_common_queries: list):
    selected_countries = ["United States", "UNITED STATES", "United States (+1)"]
    try:
        logger.info("Country question found — selecting appropriate country...")

        # Wait for the dropdown <select> element inside the question
        dropdown_element = await question_ele.query_selector("select")
        if not dropdown_element:
            logger.warning("Dropdown <select> element not found.")
            return False

        # Get all available option texts
        options = await dropdown_element.query_selector_all("option")
        available_options = [
            await (await opt.get_property("innerText")).json_value()
            for opt in options
        ]

        # Try selecting one of the desired countries
        for country in selected_countries:
            if country in available_options:
                try:
                    await dropdown_element.scroll_into_view_if_needed()  # ✅ Fixed typo here
                    await dropdown_element.select_option(label=country)
                    logger.info(f"Successfully selected country: {country}")
                    skip_common_queries.append(index)
                    return True
                except Exception as e:
                    logger.error(f"Failed to select {country}: {e}")
                    return False

        logger.warning("Desired country not found in options.")
        return True  # returns True so it doesn't block the rest of the form

    except Exception as e:
        logger.error(f"Error while handling country selection: {e}")
        return False

# this function are handle degree section
async def handle_degree_selection(page: Page, question_ele: Locator, question: str, index: int, skip_common_queries: list):
    degrees = ["Bachelors Degree"]
    try:
        logger.info("Degree question found — selecting appropriate degree...")

        # Wait for the dropdown <select> element inside the question
        dropdown_element = await question_ele.query_selector("select")
        if not dropdown_element:
            logger.warning("Dropdown <select> element not found.")
            return False

        # Get all available option texts
        options = await dropdown_element.query_selector_all("option")
        available_options = [
            await (await opt.get_property("innerText")).json_value()
            for opt in options
        ]

        # Try selecting one of the desired countries
        for degree in degrees:
            if degree in available_options:
                try:
                    await dropdown_element.scroll_into_view_if_needed()  # ✅ Fixed typo here
                    await dropdown_element.select_option(label=degree)
                    logger.info(f"Successfully selected Degree: {degree}")
                    skip_common_queries.append(index)
                    return True
                except Exception as e:
                    logger.error(f"Failed to select {degree}: {e}")
                    return False

        logger.warning("Desired degree not found in options.")
        return True  # returns True so it doesn't block the rest of the form

    except Exception as e:
        logger.error(f"Error while handling degree selection: {e}")
        return False

# this one function are handle date question
async def handle_date_selection(page: Page, question_ele:Locator, question:str, index:int, skip_common_queries: list):
        try:
            logger.info("Date question are found and we are skipping...")
            input_count = await question_ele.locator("input").count()
            if input_count > 0:
                skip_common_queries.append(index)
                return True
        except Exception as e:
            logger.warning(f"Error handle dates: {e}")
        return False

# this function are handle ethnicity section
async def handle_ethnicity_selection(page: Page, question_ele: Locator, question: str, index: int, skip_common_queries: list):
    ethnicities = ["Asian (Not Hispanic or Latino)"]
    try:
        logger.info("Athnicity question found — selecting appropriate Athnicity...")

        # Wait for the dropdown <select> element inside the question
        dropdown_element = await question_ele.query_selector("select")
        if not dropdown_element:
            logger.warning("Dropdown <select> element not found.")
            return False

        # Get all available option texts
        options = await dropdown_element.query_selector_all("option")
        available_options = [
            await (await opt.get_property("innerText")).json_value()
            for opt in options
        ]

        # Try selecting one of the desired countries
        for ethnicity in ethnicities:
            if ethnicity in available_options:
                try:
                    await dropdown_element.scroll_into_view_if_needed()  # ✅ Fixed typo here
                    await dropdown_element.select_option(label=ethnicity)
                    logger.info(f"Successfully selected athnicity: {ethnicity}")
                    skip_common_queries.append(index)
                    return True
                except Exception as e:
                    logger.error(f"Failed to select {ethnicity}: {e}")
                    return False

        logger.warning("Desired athnicity not found in options.")
        return True  # returns True so it doesn't block the rest of the form

    except Exception as e:
        logger.error(f"Error while handling athnicity selection: {e}")
        return False

# this function are handle gender section
from playwright.async_api import Page, Locator
import logging

logger = logging.getLogger(__name__)

async def handle_gender_selection(page: Page, question_ele: Locator, question: str, indext: int, skip_common_quries: list):
    """
    Handles gender selection fields (e.g., Male/Female/Other).
    """
    responses = ["male", "man"]  # normalized match keywords

    # Get all radio inputs in the question
    radio_inputs = await question_ele.query_selector_all("input[type='radio']")

    for radio in radio_inputs:
        try:
            # Get the parent label (for text)
            label = await radio.query_selector("xpath=..")
            if not label:
                continue

            label_text = (await label.inner_text()).strip().lower()

            # Check if any response keyword matches
            if any(resp == label_text for resp in responses):
                await label.click()
                logger.info(f"✓ Successfully selected gender option: {label_text}")
                skip_common_quries.append(indext)
                return True

        except Exception as e:
            logger.warning(f"⚠️ Error selecting gender option: {e}")

    logger.info("❌ No matching gender option found.")
    return False

async def handle_phone_number(page: Page, question_ele: Locator, question: str, index: int, skip_common_queries: list):
    """
    Handles questions that expect a phone number input on a form page.

    Args:
        page (Page): Playwright page instance.
        question_ele (Locator): The locator element for the current question.
        question (str): The question text (used for context or matching).
        index (int): The current question index.
        skip_common_queries (list): List of indices for questions already handled.

    Returns:
        bool: True if the phone number was successfully filled, False otherwise.
    """
    response = "15551234567"  # Example default phone number
    try:
        # Find all text input fields within this question
        inputs = await question_ele.query_selector_all("input[type='text']")

        if not inputs:
            logger.warning(f"No text input found for question: '{question}'")
            return False

        # Fill the first text input with the phone number
        await inputs[0].fill(response)
        logger.info(f"Filled phone number '{response}' for question: '{question}'")

        # Mark this question as handled
        skip_common_queries.append(index)
        return True

    except Exception as e:
        logger.warning(f"Error while filling phone number for question '{question}': {e}")
        return False

# this function are handle veteran section
async def handle_veteran_selection(page:Page, question_ele:Locator, question:str, indext:int, skip_common_quries:list):

    response = "I am not a protected veteran"

    # Get all radio inputs in the question
    radio_inputs = await question_ele.query_selector_all("input[type='radio']")
    
    for radio in radio_inputs:
        try:
            # Get the parent label
            label = await radio.query_selector("xpath=..")  # parent element
            if not label:
                continue
                
            label_text = (await label.inner_text()).strip()
            
            # Check if response matches label text
            if response.strip().lower() in label_text.lower():
                await label.click()
                logger.info(f"✓ Successfully select {response} radio.)")
                skip_common_quries.append(indext)
                return True
                
        except Exception as e:
            logger.warning(f"Error to select {response} radio button): {e}")
    
    return False

# for application submitter handel special question
async def handle_special_questions(page: Page, question_ele:Locator, question:str, index:int, skip_common_queries: list):
        if "Cover Letter" in question:
            return await handle_cover_letter(page, question_ele, question, index, skip_common_queries)
        elif "Country" in question:
            return await handle_country_selection(page, question_ele, question, index, skip_common_queries)
        elif "Please list 2-3 dates" in question:
            return await handle_date_selection(page, question_ele, question, index, skip_common_queries)
        elif "Degree" in question:
            return await handle_degree_selection(page, question_ele, question, index, skip_common_queries)
        elif "Race and Ethnicity" in question:
            return await handle_ethnicity_selection(page, question_ele, question, index, skip_common_queries)
        elif "Gender" in question:
            return await handle_gender_selection(page, question_ele, question, index, skip_common_queries)
        
        elif "Veteran" in question:
            return await handle_veteran_selection(page, question_ele, question, index, skip_common_queries)
        elif "Phone Number" in question:
            return await handle_phone_number(page, question_ele, question, index, skip_common_queries)
        
        return False

async def identify_input_type(question_ele):
    try:
        # Check for <input> fields
        input_elements = await question_ele.query_selector_all("input")
        if input_elements:
            input_type = await input_elements[0].get_attribute("type")
            return f"Input Field (Type: {input_type})"

        # Check for <textarea>
        textarea_elements = await question_ele.query_selector_all("textarea")
        if textarea_elements:
            return "Textarea"

        # Check for radio buttons
        radio_elements = await question_ele.query_selector_all("input[type='radio']")
        if radio_elements:
            return "Radio Button"

        # Check for checkboxes
        checkbox_elements = await question_ele.query_selector_all("input[type='checkbox']")
        if checkbox_elements:
            return "Checkbox"

        # Check for dropdowns
        select_elements = await question_ele.query_selector_all("select")
        if select_elements:
            return "Dropdown Select"

        # Check for fieldsets (multiple inputs)
        fieldset_elements = await question_ele.query_selector_all("fieldset")
        if fieldset_elements:
            return "Fieldset (Multiple Inputs)"

        # Check for buttons
        button_elements = await question_ele.query_selector_all("button")
        if button_elements:
            return "Button"

        # Default case
        return "Unknown"

    except Exception as e:
        return f"Error identifying input type: {e}"

# === The below one class are handle application ===
class FormHandler:
    def __init__(self, page: Page):
        self.page = page

    async def handle_radio_groups(self, question_ele, response, responses_index):
        # Get all radio inputs in the question
        radio_inputs = await question_ele.query_selector_all("input[type='radio']")
        
        for radio in radio_inputs:
            try:
                # Get the parent label
                label = await radio.query_selector("xpath=..")  # parent element
                if not label:
                    continue
                    
                label_text = (await label.inner_text()).strip()
                
                # Check if response matches label text
                if response.strip().lower() == label_text.lower():
                    await label.click()
                    logger.info(f"✓ Selected: {label_text} (Q{responses_index + 1})")
                    return True
                    
            except Exception as e:
                logger.warning(f"Radio group error (Q{responses_index + 1}): {e}")
        
        return False
    
    async def handle_checkboxes(self, question_ele, response, responses_index):
        try:
            if isinstance(response, str):
                response_list = re.split(r',', response)
                response_list = [r.strip().lower() for r in response_list if r.strip()]
            else:
                logger.warning(f"Invalid response type for Q{responses_index + 1}: {type(response)}")
                return False


            checkbox_inputs = await question_ele.query_selector_all("input[type='checkbox']")
            if not checkbox_inputs:
                logger.warning(f"No checkboxes found for Q{responses_index + 1}")
                return False

            found_any = False

            for checkbox in checkbox_inputs:
                label = await checkbox.query_selector("xpath=..")
                label_text = (await label.inner_text()).strip().lower() if label else ""
                input_value = (await checkbox.get_attribute("value") or "").lower()

                for target in response_list:
                    if target == label_text or target == input_value:
                        is_checked = await checkbox.is_checked()
                        if not is_checked:
                            await checkbox.check(force=True)
                            logger.info(f"✓ Checked: '{label_text}' (Q{responses_index + 1})")
                        found_any = True
                        break

            if not found_any:
                logger.warning(f"No matching checkboxes clicked for Q{responses_index + 1}")
                return False

            return True

        except Exception as e:
            logger.error(f"Checkbox handler failed (Q{responses_index + 1}): {e}")
            return False

    async def handle_dropdowns(self, question_ele, response, responses_index):
        dropdowns = await question_ele.query_selector_all("select")
        if dropdowns:
            try:
                # Try selecting by label first (most common)
                await dropdowns[0].select_option(label=response.strip())
                logger.info(f"✓ Dropdown selected: {response.strip()} (Q{responses_index + 1})")
                return True
            except Exception as e:
                # If label selection fails, try by value or text content
                logger.warning(f"Dropdown label selection failed (Q{responses_index + 1}), trying alternatives: {e}")
                try:
                    # Try selecting by value if response matches option value
                    await dropdowns[0].select_option(value=response.strip())
                    logger.info(f"✓ Dropdown selected by value: {response.strip()} (Q{responses_index + 1})")
                    return True
                except Exception as e2:
                    logger.warning(f"Dropdown value selection also failed (Q{responses_index + 1}): {e2}")
                    # Try manual option matching as fallback
                    return await self.handle_dropdown_manual(question_ele, response, responses_index, dropdowns[0])
        return False

    async def handle_dropdown_manual(self, question_ele, response, responses_index, dropdown):
        """Manual fallback for dropdown selection"""
        try:
            # Get all options
            options = await dropdown.query_selector_all("option")
            for option in options:
                option_text = (await option.inner_text()).strip()
                option_value = await option.get_attribute("value")
                
                # Check if response matches option text or value
                if (response.strip().lower() in option_text.lower() or 
                    response.strip().lower() in (option_value or "").lower()):
                    
                    # Use JavaScript to set the value
                    await dropdown.evaluate(f"(element) => element.value = '{option_value}'")
                    # Trigger change event
                    await dropdown.dispatch_event("change")
                    logger.info(f"✓ Dropdown manually selected: {option_text} (Q{responses_index + 1})")
                    return True
                    
        except Exception as e:
            logger.warning(f"Manual dropdown selection failed (Q{responses_index + 1}): {e}")
        
        return False


    async def handle_text_inputs(self, question_ele, response, responses_index,typing_speed):
        inputs = await question_ele.query_selector_all("input:not([type='checkbox']):not([type='radio'])")
        if inputs:
            try:
                await inputs[0].fill("")  
                await inputs[0].type(response, delay=typing_speed)
                logger.info(f"✓ Filled text input: {response} (Q{responses_index + 1})")
                return True
            except Exception as e:
                logger.warning(f"Text input error (Q{responses_index + 1}): {e}")
        return False

    async def handle_textareas(self, question_ele, response, responses_index, typing_speed:int):
        textareas = await question_ele.query_selector_all("textarea")
        if textareas:
            try:
                await textareas[0].fill("")  
                await textareas[0].type(response, delay=typing_speed)
                logger.info(f"✓ Filled textarea: {response} (Q{responses_index + 1})")
                return True
            except Exception as e:
                logger.warning(f"Textarea error (Q{responses_index + 1}): {e}")
        else:
            logger.warning(f"No textarea found (Q{responses_index + 1})")
        return False
    

async def fill_questions_form(page: Page, questions_ele: Locator, skip_common_quries: list[int], list_of_responses: list[str]) -> None:
    # Create object of formHandler
    try:
        formhandler = FormHandler(page)
        logger.info("Successfully created FormHandler object.")
    except Exception as e:
        logger.critical(f"❌ Failed to create FormHandler: {e}")
        return False
    
    # Count quuestions_ele for iterating.
    count = await questions_ele.count()
    responses_index = 0

    # Iterate question_ele and put response from list_of_responses.
    for i in range(count):

        # if index in skip_common_quries or responses_index >= list_of_responses.
        if i in skip_common_quries or responses_index >= len(list_of_responses):
            continue

        # Convert Locator → ElementHandle
        question_ele = await questions_ele.nth(i).element_handle()
        
        # get response from list_of_responses base on index because some question may be skiped.
        response = list_of_responses[responses_index]
        responses_index += 1

        # Jump back to loop if response empty.
        if not response.strip():
            logger.info(f"Empty response skipped for Q{i+1}")
            continue
        try:
            try:
                # Scroll to question element first.
                await questions_ele.nth(i).scroll_into_view_if_needed(timeout=60000)
                # logger.info(f"Scrolled to question {i+1}")
                await asyncio.sleep(random.uniform(1, 3))
                # await aioconsole.ainput("Debug and press enter.")
            except Exception as e:
                logger.warning("Did not scrolled to question elementl: {e}")
            
            handled = (
                await formhandler.handle_radio_groups(question_ele, response, i)
                or await formhandler.handle_checkboxes(question_ele, response, i)
                or await formhandler.handle_dropdowns(question_ele, response, i)
                or await formhandler.handle_text_inputs(question_ele, response, i,typing_speed=config_input.typing_speed)
                or await formhandler.handle_textareas(question_ele, response, i,typing_speed=config_input.typing_speed)
            )

            if not handled:
                logger.info(f"No suitable input found for Q{i+1}")

        except Exception as e:
            logger.error(f"❌ Error handling Q{i+1}: {e}")


# === Method are create full request of app quries to send ai to get res ===
async def create_form_quries_prompt(job: dict, list_of_queries) -> str:
    try:
        # Build the query list first
        formatted_queries = "\n".join(f"{i+1}. {q}" for i, q in enumerate(list_of_queries))

        # Then safely construct the prompt
        prompt = f"""{config_input.form_question_prompt}
JOB DETAILS:
Position: {job.get('job_title', 'N/A')}
Key Points: {job.get('job_details_section', 'N/A')}

QUERY LIST:
{formatted_queries}
"""
        if config_input.show_prompt_for_form_quries:
            logger.info(f"Complete prompt:\n{prompt}")

        return prompt
    except Exception as e:
        logger.critical(f"Error in creating_form_quries_request: {e}")
        return ""


# Geting application quries responses
async def get_form_questions_and_coverletter_responses(prompt):
    model_response = None
    try:
        model_response = await get_match_percentage_from_gemini(prompt)
        logger.info(f"Gemini response type: {type(model_response)}:\n{model_response}")
    except ResourceExhausted as e:
        logger.error(f"Gemini quota exceeded, falling back to Groq...{e}")
    except Exception as e:
        logger.error(f"Error from Gemini:{e}")

    # Fallback if Gemini fails or returns None
    if not model_response:
        try:
            model_response = await get_match_percentage_from_groq(prompt)
            if config_input.show_ai_response_for_form_quries:
                logger.info(f"Groq response type{str(model_response)}: {model_response}")
        except Exception as e:
            logger.error(f"Error from Groq:")
            model_response = None  # Optional: keep as None for later handling

    return model_response

async def take_screenshot(page, folder_path, screenshot_name):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        await page.screenshot(
            path=f"{folder_path}/{screenshot_name}_{timestamp}.png",
            full_page=True
        )
        logger.info(f"Successfully save screenshot: {folder_path}/{screenshot_name}_{timestamp}.png")
    except Exception as e:
        logger.warning(f"Error to take screenshot: {e}")


async def wait_for_page_to_load(page: Page, btn_name: str, current_url):
    """
    Waits for the page to fully load after clicking a button.
    Captures a screenshot if load fails.
    """
   # befor starting wait first to change url
    try:
        current_url = current_url
        await page.wait_for_function(
            f"window.location.href !== '{current_url}'",
            timeout=config_input.wait_for_change_url_dectect)
    except Exception as e:
        await take_screenshot(page, config_input.DEBUGGING_SCREENSHOTS_PATH, "page_url_not_changed")
        logger.warning(f"page url not changed by click continue|other btns: {page.url}")
        return False
   
    try:
        # once change urls then wait for page content to load
        await asyncio.sleep(2)
        await page.wait_for_load_state("load", timeout=config_input.wait_for_page_to_load)
        await asyncio.sleep(4)
        logger.info(f"Page fully loaded after clicking '{btn_name}' button.")
        return True
    except Exception as e:
        await take_screenshot(page,config_input.DEBUGGING_SCREENSHOTS_PATH,"page_not_load")
        # Log warning with precise info
        logger.warning(
            f"Page did not load within {config_input.wait_for_page_to_load / 1000:.1f}s "
            f"after clicking '{btn_name}' button: {e}"
        )
        await page.close() # close page if page not load
        return False

async def smooth_scroll_to_page_bottom(page, scroll_step=1000, scroll_delay=0.3, max_idle_rounds=5):
    """
    Smoothly scrolls to the bottom of a dynamically loading page.

    Args:
        page: Playwright Page object.
        scroll_step (int): Pixels to scroll each time.
        scroll_delay (float): Delay (in seconds) between scrolls.
        max_idle_rounds (int): How many times to check for no change before stopping.
    """
    previous_height = await page.evaluate("document.body.scrollHeight")
    idle_rounds = 0

    while True:
        # Scroll down
        await page.evaluate(f"window.scrollBy({{ top: {scroll_step}, behavior: 'smooth' }});")
        await asyncio.sleep(scroll_delay)

        # Wait a bit for content to load
        current_height = await page.evaluate("document.body.scrollHeight")

        if current_height == previous_height:
            idle_rounds += 1
        else:
            idle_rounds = 0
            previous_height = current_height

        # If we've seen no change for a few rounds, stop
        if idle_rounds >= max_idle_rounds:
            break

    # logger.info("Fully page scrolled to bottom.")

async def update_cover_letter(page:Page, job:dict):
    try:
        # try to click on add button for cover letter
        add_btn = page.locator('[data-testid="application-preview"]').content_frame.get_by_role("button", name="Add Supporting documents")
        await add_btn.click()
        logger.info("Successfully clicked on 'Add Supporting documents' button.")
        # Try to click on write_cover_letter box
        try:
            write_cover_letter_box = page.get_by_text("Write a cover letter", exact=True)
            await write_cover_letter_box.click()
            logger.info("Successfully click on cover letter option btn.")
            # if user want to write new cover for jobs.
            if config_input.write_new_coverletter_for_job:
                await write_cover_letter(page=page, job=job)
        except Exception as e:
            logger.warning(f"Error on click write_cover_letter_box: {e}")
        # Click on update button
        try:
            current_url=page.url  # /additional-documents
            continue_btn = page.locator("button[data-testid$='continue-button']")
            await continue_btn.click()
            logger.info("Successfully click on update cover letter button.")
            await wait_for_page_to_load(page=page, btn_name="Update cover letter", current_url=current_url)
            await page.wait_for_selector("text='Submit your application'", timeout=config_input.wait_for_review_page_loading)
        except Exception as e:
            logger.warning(f"Error to click on update cover letter button.\n {e}")
    except Exception as e:
        logger.warning(f"Error clicking on 'Add Supporting documents': {e}")
        await take_screenshot(page,config_input.DEBUGGING_SCREENSHOTS_PATH,"cover_letter_not_found")


async def create_coverletter_prompt(job: dict) -> str:
    """
    This one function are crating and return prompt request for write best cover letter for provided job.
    """
    try:
        # Then safely construct the prompt
        prompt =f"""
{config_input.ai_prompt_for_writing_coverletter}
{job}
        """
        if config_input.show_prompt_for_writing_coverletter:
            logger.info(f"Complete prompt:\n{prompt}")
        return prompt
    except Exception as e:
        logger.critical(f"Error in creating_coverletter_request: {e}")
        return ""
    

async def write_cover_letter(page:Page, job:dict):
    "This function are writing cover letter."
    try:
        prompt = await create_coverletter_prompt(job=job)
        coverletter = await get_form_questions_and_coverletter_responses(prompt=prompt)
        logger.info("We are writing cover letter...")
        selector = 'textarea[data-testid="cover-letter-radio-card-text-area"]'
        # Wait for textarea to appear
        await page.wait_for_selector(selector)
        # Get the element handle
        textarea = await page.query_selector(selector)
        # Scroll into view before typing
        await textarea.scroll_into_view_if_needed()
        # Clear existing text (if any)
        await page.fill(selector, "")
        # Type the cover letter with adjustable typing speed
        await page.type(selector, coverletter, delay=config_input.writing_cover_letter_speed)
        logger.info("Successfully typed cover letter.")
    except Exception as e:
        logger.warning(f"Error in writing cover letter: \n {e}")    
