import urllib.parse
import traceback, os, shutil, csv
from dotenv import load_dotenv
from playwright.async_api import Page
import google.generativeai as genai
import asyncio, random
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
import asyncio
import aiofiles
import csv
import io
from playwright.async_api import Locator


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
    
    # Initial pause before interaction (thinking, observing)
    # await asyncio.sleep(random.uniform(0.2, 0.5))  # much shorter initial delay

    # Simulate scrolling (like someone casually reading)
    for _ in range(random.randint(1, 2)):  # fewer scrolls
        scroll_amount = random.randint(100, 200)  # smaller scroll amount
        await page.mouse.wheel(0, scroll_amount)
        await asyncio.sleep(random.uniform(0.2, 0.5))  # shorter wait between scrolls

    # # Move mouse quickly (simulate hand movement)
    # await page.mouse.move(
    #     random.randint(0, 800),
    #     random.randint(0, 600),
    #     steps=random.randint(5, 10)  # fewer steps for faster movement
    # )
    # await asyncio.sleep(random.uniform(0.2, 0.5))  # short idle pause

    # Scroll to bottom like a user might do
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(random.uniform(0.5, 1.0))  # shorter after-scroll wait

    # # Optional: small extra move to simulate curiosity
    # await page.mouse.move(
    #     random.randint(0, 800),
    #     random.randint(0, 600),
    #     steps=random.randint(5, 10)  # fewer steps for faster movement
    # )
    # await asyncio.sleep(random.uniform(0.2, 0.5))  # short idle pause


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


async def get_match_percentage(prompt):
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
async def wait_until_internet_is_back(page):
    print("❌ Internet connection lost. Waiting to reconnect...")
    while not await check_internet():
        await asyncio.sleep(10)
    print("✅ Internet reconnected.")
    await page.reload()


# upload cover letter function
async def upload_coverletter_and_submit_application(page):
   # Try to click "Add Support Documents"
    try:
        add_btn = await page.locator("//a[@aria-label='Add Supporting documents']", timeout=10000)
        # Scroll to btn
        await page.evalate("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", add_btn)
        # Click on that
        add_btn.click()
        logger.info("Successfully click on Add Supporting documents.")
    except Exception as e:
        logger.warning(f"Error click on Add Supporting documents.\n {e}")
        
    # Click on cover letter option and update btn
    try:
        add_btn = await page.locator("//label[@data-testid='CoverLetterRadioCard-label']", timeout=10000)
        # Scroll to btn
        await page.evalate("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", add_btn)
        add_btn.click()
        logger.info("Successfully click on cover letter option btn.")
        
        # Click on update button
        try:
            update_btn = await page.locator("//label[@data-testid='CoverLetterRadioCard-label']", timeout=10000)
            # Scroll to btn
            await page.evalate("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", update_btn)
            update_btn.click()
            logger.info("Successfully click on update btn.")
        except Exception as e:
            logger.warning(f"Error to click on update btn.\n {e}")
    except Exception as e:
        logger.warning(f"Error to click on cover letter option btn.\n {e}")

    # Try to click on submit button
    try:
        submit_button = await page.locator("//span[normalize-space()='Submit your application']")
        await page.evalate("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_button)
        submit_button.click()
        logger.info("✅ Application submitted successfully!")
    except Exception as e:
        logger.warning("Error to click on submit button.")

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
    logger.info("Job all informatios are saved in CSV.")
    # Write asynchronously to file
    try:
        async with aiofiles.open(file_path, mode='a', newline='') as f:
            await f.write(buffer.getvalue())
            logger.info("Job info successfully append to csv.")
    except Exception as e:
        logger.warning("Error to append jobs data to csv.")
    return False
    


# === below are some best function for handle common quries in jobs application ===


async def handle_cover_letter(page: Page, question_ele:Locator, question:str, index:int, skip_common_queries: list):
    try:
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

# this one function are gonna to solve country related question
async def handle_country_selection(page: Page, question_ele:Locator, question:str, index:int, skip_common_queries: list):
    selected_countries = ["United States", "United States (+1)"]
    try:
        # Wait for the dropdown <select> element inside the question
        dropdown_element = await question_ele.query_selector("select")
        if not dropdown_element:
            logger.warning("Dropdown <select> element not found.")
            return False

        # Get all option texts
        options = await dropdown_element.query_selector_all("option")
        available_options = [await (await opt.get_property("innerText")).json_value() for opt in options]

        # Try selecting one of the desired countries
        for country in selected_countries:
            if country in available_options:
                try:
                    await dropdown_element.select_option(label=country)
                    logger.info(f"Successfully selected country: {country}")
                    skip_common_queries.append(index)
                    return True
                except Exception as e:
                    logger.error(f"Failed to select {country}: {e}")
                    return False

        logger.warning("Desired country not found in options.")
        return True

    except Exception as e:
        logger.error(f"Error while handling country selection: {e}")
        return False

# this one function are handle date question
async def handle_date_selection(page: Page, question_ele:Locator, question:str, index:int, skip_common_queries: list):
        try:
            input_count = await question_ele.locator("input").count()
            if input_count > 0:
                skip_common_queries.append(index)
                return True
        except Exception as e:
            logger.warning(f"Error handle dates: {e}")
        return False

# for application submitter handel special question
async def handle_special_questions(page: Page, question_ele:Locator, question:str, index:int, skip_common_queries: list):
        if "Cover Letter" in question:
            return await handle_cover_letter(page, question_ele, question, index, skip_common_queries)
        elif "Country" in question:
            return await handle_country_selection(page, question_ele, question, index, skip_common_queries)
        elif "Please list 2-3 dates" in question:
            return await handle_date_selection(page, question_ele, question, index, skip_common_queries)
        return False

# this one function are gonna indentify question field input types
async def identify_input_type(question_ele):
    # Check for <input> fields
    input_elements = await question_ele.query_selector_all("input")
    if input_elements:
        input_element = input_elements[0]
        input_type = await (await input_element.get_attribute("type"))
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


# === The below one class are handle application ===
class FormHandler:
    def __init__(self, page: Page):
        self.page = page

    async def handle_radio_groups(self, question, response, index):
        radio_groups = await question.query_selector_all("fieldset[role='radiogroup']")
        if radio_groups:
            for group in radio_groups:
                labels = await group.query_selector_all("label")
                for label in labels:
                    try:
                        option = await label.query_selector("span.css-l5h8kx, span.css-1br6eau")
                        if option:
                            option_text = (await option.inner_text()).strip()
                            if response.strip().lower() in option_text.lower():
                                await label.click()
                                logger.info(f"✓ Selected: {option_text} (Question {index + 1})")
                                return True
                    except Exception as e:
                        logger.warning(f"⚠️ Error in radio group {index + 1}: {e}")
                        continue
        return False

    async def handle_checkboxes(self, question, response, index):
        checkbox_groups = await question.query_selector_all(
            "fieldset[role='group'], fieldset.ia-MultiselectQuestion"
        )
        if checkbox_groups:
            for group in checkbox_groups:
                labels = await group.query_selector_all("label")
                for label in labels:
                    try:
                        option = await label.query_selector("span.css-l5h8kx, span.css-1br6eau")
                        checkbox_input = await label.query_selector("input")
                        if option and checkbox_input:
                            option_text = (await option.inner_text()).strip()
                            checked = await checkbox_input.is_checked()
                            if checked:
                                logger.info(f"✓ Already Checked: {option_text} (Skipping Question {index + 1})")
                                continue
                            if response.strip().lower() in option_text.lower():
                                await label.click()
                                logger.info(f"✓ Checked: {option_text} (Question {index + 1})")
                                return True
                    except Exception as e:
                        logger.warning(f"⚠️ Error in checkbox group {index + 1}: {e}")
                        continue
        return False

    async def handle_dropdowns(self, question, response, index):
        dropdowns = await question.query_selector_all("select")
        if dropdowns:
            try:
                dropdown = dropdowns[0]
                await dropdown.select_option(label=response.strip())
                logger.info(f"✓ Selected dropdown: {response.strip()} (Question {index + 1})")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Dropdown error in Question {index + 1}: {e}")
        return False

    async def handle_text_inputs(self, question, response, index):
        inputs = await question.query_selector_all("input:not([type='checkbox']):not([type='radio'])")
        if inputs:
            try:
                input_box = inputs[0]
                await input_box.fill("")  # clear input
                await input_box.type(response)
                logger.info(f"✓ Filled text input: {response} (Question {index + 1})")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Text input error in Question {index + 1}: {e}")
        return False

    async def handle_textareas(self, question, response, index):
        textareas = await question.query_selector_all("textarea")
        if textareas:
            try:
                textarea = textareas[0]
                await textarea.fill("")  # clear textarea
                await textarea.type(response)
                logger.info(f"✓ Filled textarea: {response} (Question {index + 1})")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Textarea error in Question {index + 1}: {e}")
        else:
            logger.warning(f"⚠️ No textarea found for Question {index + 1}, skipping...")
        return False


# === Method are create full request of app quries to send ai to get res ===
async def get_form_questions_request(job_title, job_details_section, list_of_queries):
    prompt = f"""{config_input.form_question_promtp}
    JOB DETAILS:
    Position: {job_title}
    Key Points: {job_details_section}

    QUERY LIST:
    {''.join(f"{i+1}. {q}" for i, q in enumerate(list_of_queries))}

"""
    if config_input.show_prompt_of_quries_and_responses:
        logger.info(f"Complete prompt: \n \n {prompt}")
    return prompt

# Geting application quries responses
async def get_question_responses(prompt):
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


async def click_continue_button(page, btn_name):
    """Click visible 'Continue' button (iframe or main page)."""
    try:
        await asyncio.sleep(5)
        await simulate_human_behavior(page=page)
        logger.info(f"⏳ Searching for {btn_name} 'Continue' button...")

        
        # 1️⃣ Search inside iframes
        for frame in page.frames:
            if any(k in frame.url for k in ["indeedapply", "apply"]):
                logger.info(f"🔍 Checking iframe: {frame.url}")
                try:
                    buttons = frame.locator("button:has-text('Continue')")
                    for i in range(await buttons.count()):
                        btn = buttons.nth(i)
                        if await btn.is_visible():
                            await btn.click()
                            logger.info(f"✅ Clicked 'Continue' inside iframe (#{i}).")
                            found = True
                            break
                    if found:
                        break
                except Exception as e:
                    logger.warning(f"⚠️ Error accessing iframe: {e}")

        # 2️⃣ Search on main page if not found
        if not found:
            buttons = page.locator("button:has-text('Continue')")
            count = await buttons.count()
            logger.info(f"Found {count} 'Continue' buttons on main page.")
            for i in range(count):
                btn = buttons.nth(i)
                if await btn.is_visible():
                    await btn.scroll_into_view_if_needed()
                    await btn.click()
                    logger.info(f"✅ Clicked 'Continue' button on main page (#{i}).")
                    found = True
                    break

        if not found:
            logger.warning("❌ No visible or clickable 'Continue' button found.")
            return False

        return True
    except Exception as e:
        logger.error(f"❌ Unexpected error while clicking 'Continue': {e}")
        return False