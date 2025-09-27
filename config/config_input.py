import gspread,random
from google.oauth2.service_account import Credentials

def load_scraper_config_from_sheet():
    creds_path = "config/indeed_spider_gs_credentails.json"
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
    date_posted = int(settings_dict.get("DATE_POSTED", 0)),
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
        for f in settings_dict.get("SHEETS_NAMES", "").split(",")
        if f.strip()
    ]

    config = {
        "CONCURRENT__SIZE": int(settings_dict.get("CONCURRENT__SIZE", 6)),
        "MATCHING_PERCENTAGE": int(settings_dict.get("MATCHING_PERCENTAGE", 50)),
        "LEAVE_BLANK_COLLS": int(settings_dict.get("LEAVE_BLANKS_COLLS", 2)),
        "AI_PROMPT": settings_dict.get("AI_PROMPT", ""),
        "RESUME": settings_dict.get("RESUME", ""),
        "PER_COMPANY_JOBS": int(settings_dict.get("PER_COMPANY_JOBS", 2)),
        "PROCESS_BATCH_SIZE": int(settings_dict.get("PROCESS_BATCH_SIZE", 15)),
        "CSV_FILES": csv_files,
        "WORKBOOK_ID": settings_dict.get("WORKBOOK_ID", ""),

        # Other sheets
        "JOBS_LISTED_PAGES_URLS": load_column("JobUrls", date_posted[0]),
        "CONFIRMATION_COMPANIES": load_column("ConfirmationCompanies"),
        "IGNORE_COMPANIES": load_column("IgnoreCompanies"),
    }

    return config


# === Usage ===
config = load_scraper_config_from_sheet()

# JOBS SEARCH LINKS
jobs_listed_pages_urls = [
    url.strip()
    for url in config["JOBS_LISTED_PAGES_URLS"]
    if url.strip() and "indeed.com" in url
]

# Scraper setting vars
MATCHING_PERCENTAGE = config["MATCHING_PERCENTAGE"]
CSV_FILES = [file + ".csv" for file in config["CSV_FILES"]]
LEAVE_BLANK_COLLS = config["LEAVE_BLANK_COLLS"]
PER_COMPANY_JOBS = config["PER_COMPANY_JOBS"]
PROCESS_BATCH_SIZE = config["PROCESS_BATCH_SIZE"]
WORKBOOK_ID = config["WORKBOOK_ID"]
AI_PROMPT = config["AI_PROMPT"]
RESUME = config["RESUME"]


# Ignore some companies jobs while scraping jobs
ignore_companies = config["IGNORE_COMPANIES"]
# High Preority/Confirmation companies
confirmation_companies = config["CONFIRMATION_COMPANIES"]


PROCESSED_JOBS_FILE_PATH = r'input\\processed_jobs.txt'
DEBUGGING_SCREENSHOTS_PATH = "debugging_screenshots"

# on/off headless mode
headless = True


RANDOM_SLEEP = random.randint(1,3)

gemini_model_version = "gemini-2.0-flash"


AVIOD_JOBS = ["clearance", "government", "cyber"]


MAX_CONTEXTS = config["CONCURRENT__SIZE"]

keep_processed_jobs_links = 8000



