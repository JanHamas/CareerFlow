from pathlib import Path
from datetime import datetime
import random

# on/off headless mode
headless = False

# get the main project dir
BASE_DIR = Path(__file__).resolve().parent.parent


# Scraper setting vars
jobs_listed_pages_urls = [
"https://www.indeed.com/jobs?q=power+bi+analyst&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=nlp&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=matlab&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=artificial+intelligence&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=mlops&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=transformer&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=python+developer&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=tensorflow&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=pytorch&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=data+engineer&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=etl+developer&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=ai+testing&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=analytics+engineer&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=ai+engineer&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=statistical+analyst&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=data+scientist&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=machine+learning+engineer&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=deep+learning&l=United+States&fromage=1",
"https://www.indeed.com/jobs?q=databricks&l=United+States&fromage=1",
]


AI_PROMPT_FOR_LISTING_JOBS = """
Analyze the resume below and calculate the highest match percentage for each provided job title. Output only the percentages as space-separated numbers in a single line, for example: 95 85 30 65. For any job title that contains the words 'manager' or 'director', assign a match percentage of 0. Do not include any other text or explanations.
"""
ABOUT_ME_FOR_LISTING_JOBS = """
 AI/ML & Data Science expert with experience in NLP, CV, and analytics. Skilled in Python, Go, SQL, PyTorch, TensorFlow, and ML tools (Scikit-learn, Hugging Face, XGBoost). Hands-on with LLMs, LangChain, AutoGPT, RAG, and model optimization. Proficient in MLOps (Docker, Kubernetes, Airflow, MLflow), cloud (AWS, GCP, Azure), and data engineering (Spark, Hive, Snowflake). Experienced in REST APIs, vector DBs (FAISS, Weaviate), and Agile teams.
"""

MAX_CONTEXTS_FOR_LISTING_JOBS = 1
MATCHING_PERCENTAGE_FOR_LISTING_JOBS = 50
PER_COMPANY_JOBS = 1
PROCESS_BATCH_SIZE = 10
CSV_FILES = ["Easy_applies.csv","CS_applies.csv"," Confirmation_applies.csv"]
AVIOD_JOBS = ["clearance", "government", "cyber"]
SAVE_CS_AND_CONFIRMATION_APPLICATIONS = True

# Ignore some companies jobs while scraping jobs
ignore_companies = []

# High Preority/Confirmation companies
confirmation_companies = []

# processed jobs file path
PROCESSED_JOBS_FILE_PATH = BASE_DIR / "config" / "processed_jobs.txt"

# Debugging screen shot folder path
DEBUGGING_SCREENSHOTS_PATH = "debugging_screenshots"

RANDOM_SLEEP = random.randint(1,3)

gemini_model_version = "gemini-2.0-flash"

keep_processed_jobs_links = 8000

INDEED_ACCOUNT_DIR_FOR_JOBS_LISTING = BASE_DIR / "utils" / "in_account_for_jobs_listing"

INDEED_ACCOUNT_DIR_FOR_APP_SUBMISSION = BASE_DIR / "config" / "indeed_account"

easy_applies_sheet_file_path = BASE_DIR / "output" / "Easy_applies.csv"


# === Vars for application submitter module ===
today_date = datetime.today().strftime("%m/%d/%Y")
form_question_prompt = f"""
Today's date: {today_date}

You are Babar Rehman — Senior Full-Stack Developer (8+ years)
Email: babarrehman.dev@gmail.com | Wake Forest, NC | (919) 918-0296
LinkedIn: linkedin.com/in/babarrehman1970
Skilled in .NET Core, C#, ASP.NET, Angular, React, Python, Django, AWS, and Azure.
Experienced in DevOps, cloud systems, and agile leadership.

Guidelines:
- Be concise, professional, and confident responses with symboles.
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
show_prompt_of_form_quries = False

# scroll step (pixels)
scrolling_step = 100 

# wait for page content to load second * Millisecond
wait_for_page_to_load = 120*1000

# try to open application for submit
try_to_open_page = 3

# printing ai response for form quries
show_ai_response_of_form_quries = True

# spider typing speed in ms
typing_speed = 0
wait_for_review_page_loading = 60*1000
wait_for_change_url_dectect = 1000*10
show_ai_prompt_for_getting_matching_percentage = False
show_ai_response_for_getting_matching_percentage= False


# cover letter section
writing_cover_letter_speed = 10  # millisecond
write_new_coverletter_for_job = True
show_prompt_for_writing_coverletter = True
ai_prompt_for_writing_coverletter = """write best and consice cover letter for below job: """


# Wait to review to see application submitted page.
wait_when_app_submitted = 3
submit_extracted_jobs = True
