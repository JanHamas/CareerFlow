import gspread, random, os
from google.oauth2.service_account import Credentials
from datetime import datetime
from pathlib import Path


# get the main project dir
BASE_DIR = Path(__file__).resolve().parent.parent
GS_CREDENTIAL_FILE_PATH = BASE_DIR / "config" / "indeed_spider_gs_credentails.json"

def load_scraper_config_from_sheet():
    creds_path = GS_CREDENTIAL_FILE_PATH
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    # Auth
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    client = gspread.authorize(creds)

    # Open sheet by fixed key (this is your config sheet)
    spreadsheet = client.open_by_key("1Fbq9XRtBApCJHvjcrUI2JCIEGZC-Mri7-pt8hfHrSWI")

    # Load Settings
    try:
        settings_data = spreadsheet.worksheet("Settings").get_all_values()
    except gspread.exceptions.WorksheetNotFound:
        raise ValueError("❌ 'Settings' sheet not found in the workbook.")

    settings_dict = {
        row[0].strip(): row[1].strip().strip('"')  # remove extra quotes if present
        for row in settings_data if len(row) >= 2 and row[0].strip()
    }

    # Helper: load specific column (default = 0 → column A, 1 → column B, etc.)
    def load_column(sheet_title, col_index=0):
        try:
            sheet = spreadsheet.worksheet(sheet_title)
            return [
                row[col_index].strip()
                for row in sheet.get_all_values()
                if row and len(row) > col_index and row[col_index].strip()
            ]
        except gspread.exceptions.WorksheetNotFound:
            return []


    # Parse comma-separated sheet names if present
    csv_files = [
        f.strip()
        for f in settings_dict.get("Sheet names", "").split(",")
        if f.strip()
    ]


    config = {

        "AI_PROMPT": settings_dict.get("AI prompt", ""),
        "RESUME": settings_dict.get("Resume", ""),
        "DATE_POSTED": settings_dict.get("Date posted", ""),
        "CONCURRENT__SIZE": int(settings_dict.get("Concurrent size", 6)),
        "MATCHING_PERCENTAGE": int(settings_dict.get("Matching percentage", 50)),
        "PER_COMPANY_JOBS": int(settings_dict.get("PER_COMPANY_JOBS", 2)),
        "LEAVE_BLANK_COLLS": int(settings_dict.get("LEAVE_BLANKS_COLLS", 2)),
        "PROCESS_BATCH_SIZE": int(settings_dict.get("Processing batch size", 15)),
        "CSV_FILES": csv_files,
        "WORKBOOK_ID": settings_dict.get("Workbook id", ""),
        "SCRAPER_RUN_TIME": settings_dict.get("Scraper run time", ""),

        # Other sheets
        "JOBS_LISTED_PAGES_URLS": load_column("JobUrls", 0),
        "CONFIRMATION_COMPANIES": load_column("ConfirmationCompanies"),
        "IGNORE_COMPANIES": load_column("IgnoreCompanies"),
    }

    return config


# === Usage ===
config = load_scraper_config_from_sheet()
days_map = {
    "24 hours": "1",
    "3 days": "3",
    "7 days": "7",
    "14 days": "14"
}

date_value = None

for key, val in days_map.items():
    if key in config["DATE_POSTED"]:
        date_value = val
        break

jobs_listed_pages_urls = [
    url.strip().replace("fromage=1", f"fromage={date_value}")
    for url in config["JOBS_LISTED_PAGES_URLS"]
    if url.strip() and "indeed.com" in url
]

# Scraper setting vars
AI_PROMPT_FOR_LISTING_JOBS = config["AI_PROMPT"]
RESUME_FOR_LISTING_JOBS = config["RESUME"]
MAX_CONTEXTS_FOR_LISTING_JOBS = config["CONCURRENT__SIZE"]
MATCHING_PERCENTAGE_FOR_LISTING_JOBS = config["MATCHING_PERCENTAGE"]
CSV_FILES = [file + ".csv" for file in config["CSV_FILES"]]
LEAVE_BLANK_COLLS = config["LEAVE_BLANK_COLLS"]
PER_COMPANY_JOBS = config["PER_COMPANY_JOBS"]
PROCESS_BATCH_SIZE = config["PROCESS_BATCH_SIZE"]
WORKBOOK_ID = config["WORKBOOK_ID"]
SCRAPER_RUNNING_TIME = config["SCRAPER_RUN_TIME"]

# Ignore some companies jobs while scraping jobs
ignore_companies = config["IGNORE_COMPANIES"] 

# High Preority/Confirmation companies
confirmation_companies = config["CONFIRMATION_COMPANIES"]


# processed jobs file path
PROCESSED_JOBS_FILE_PATH = BASE_DIR / "config" / "processed_jobs.txt"


# Debugging screen shot folder path
DEBUGGING_SCREENSHOTS_PATH = "debugging_screenshots"

# on/off headless mode
headless = False

RANDOM_SLEEP = random.randint(1,3)

gemini_model_version = "gemini-2.0-flash"

AVIOD_JOBS = ["clearance", "government", "cyber"]

MAX_CONTEXTS = config["CONCURRENT__SIZE"]

keep_processed_jobs_links = 8000


SAVE_CS_AND_CONFIRMATION_APPLICATIONS = True

INDEED_ACCOUNT_DIR = BASE_DIR / "config" / "indeed_account"

easy_applies_sheet_file_path = BASE_DIR / "output" / "Easy_applies.csv"


# === Below are complete prompt for getting responsive for ai ===
today_date = datetime.today().strftime("%m/%d/%Y")

form_question_prompt = f"""
Today's date: {today_date}

You are Babar Rehman — Senior Full-Stack Developer (8+ years)
Email: babarrehman.dev@gmail.com | Wake Forest, NC | (919) 918-0296
LinkedIn: linkedin.com/in/babarrehman1970
Skilled in .NET Core, C#, ASP.NET, Angular, React, Python, Django, AWS, and Azure.
Experienced in DevOps, cloud systems, and agile leadership.

Guidelines:
- Be concise, professional, and confident.
- Use MM/DD/YYYY for dates (provide a valid one if missing).
- One line per query — no extra text or explanations.
- Answer all queries (no skips).
- Match dropdown, radio, and checkbox options exactly (case-sensitive).
- For checkboxes, if multiple options are selected, separate them with commas.
- Maintain a formal tone.

Example:
1. 15551234567
2. No
3. linkedin.com/in/babarrehman1970
"""


# for prompt debugging
show_prompt_of_page_quries = False

# scroll step (pixels)
scrolling_step = 100 

# wait for page context to load second * Millisecond
wait_for_page_to_load = 120*1000

# try to open application for submit
try_to_open_page = 3

# printing ai response for form quries
print_ai_response_for_form_quries = True

# spider typing speed in ms
typing_speed = 0


wait_for_review_page_loading = 30*1000


wait_for_change_url_dectect = 1000*120

show_ai_prompt_for_getting_matching_percentage = False
show_ai_response_for_getting_matching_percentage= False


