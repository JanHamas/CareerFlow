🚀 Project Acquirer AI: Your Automated Project & Lead Generation Engine
Stop Chasing, Start Winning.

In the competitive landscape of IT and service provision, finding the next project shouldn't be a manual chore. It should be an automated, intelligent, and highly efficient process. Too many sales and business development teams are still sifting through countless job postings, trying to manually identify companies in need of their services. This is slow, inefficient, and costly.
Introducing Project Acquirer AI: The revolutionary solution that transforms your project acquisition strategy from reactive and manual to proactive, precise, and AI-driven.
Project Acquirer AI isn't just a scraper; it's your dedicated, 24/7 AI-powered business development assistant. It intelligently identifies and qualifies potential projects and leads from leading job boards like Indeed, matching them against your company's service offerings and expertise with unparalleled accuracy. Say goodbye to guesswork and hello to a pipeline filled with high-probability opportunities.


🎯 What is Project Acquirer AI?

Project Acquirer AI is an advanced, stealthy web automation tool designed to streamline and automate the process of identifying potential clients and projects for IT service providers, consulting firms, staffing agencies, and any business that leverages job postings for lead generation.
It mimics human behavior, bypasses sophisticated bot detection, and leverages cutting-edge AI to pinpoint opportunities that perfectly align with your company's "resume" – your service offerings, technologies, and expertise. All configurations are managed effortlessly through a simple Google Sheet, putting you in complete control without touching a single line of code.
✨ The Game-Changing Features for Sales & Business Development Teams

1. AI-Powered Hyper-Targeting & Qualification
Intelligent Matching: Forget manual keyword searches. Our system uses advanced Generative AI (Gemini/Groq) to read thousands of job descriptions and compare them against your company's capabilities (defined by your "AI Prompt" and "Resume" in the configuration).
Precision Scoring: Each potential project receives a quantifiable "matching percentage," allowing your team to focus exclusively on the highest-probability leads (e.g., only show me projects with >80% match!). This isn't just a filter; it's a qualified lead score.
Customizable AI Prompt: Tailor the AI's understanding of your services. Do you offer Cloud Migration, Custom Software Development, Cybersecurity Consulting, or Staff Augmentation? Tell the AI exactly what you're looking for, and it will find it.

2. Automated Lead Generation at Scale
24/7 Opportunity Discovery: The scraper continuously monitors job boards, identifying new projects the moment they're posted, giving you a crucial first-mover advantage.
Eliminate Manual Searching: Free up your sales team from tedious, repetitive tasks. Let them focus on what they do best: building relationships and closing deals, not hunting for leads.
Vast Lead Volume: Process hundreds or thousands of job listings in a fraction of the time it would take a human, ensuring no high-value opportunity slips through the cracks.

3. Unrivaled Stealth & Reliability
Sophisticated Anti-Detection: Equipped with Playwright Stealth, unique browser fingerprints, rotating proxies, and human-like interaction simulations, our system operates discreetly and reliably.
Cloudflare Bypass: Automatically navigates complex bot protection mechanisms, including Cloudflare challenges, ensuring uninterrupted data flow.
Duplicate Prevention: Intelligently tracks processed jobs to avoid redundant leads and ensure your team always sees fresh opportunities.

4. Effortless Management & Reporting
Google Sheet Control Panel: Manage all scraper settings – target URLs, company ignore/confirmation lists, matching thresholds, and even your AI prompt – directly from a simple, shared Google Sheet. No coding required!
Categorized Output: Projects are automatically categorized into "Easy Apply," "Company Site Apply," and "Confirmation Companies," ready for your team to act on.
Automated Google Sheet Upload: All qualified leads are automatically uploaded to designated Google Sheets, sorted by matching percentage for immediate prioritization.
Comprehensive Debugging & Email Alerts: Receive automated email reports with debugging screenshots and detailed logs, ensuring transparency and quick issue resolution even when running unattended.

5. Business Development Focused Filtering
Company Prioritization: Highlight "Confirmation Companies" for special attention or automatically "Ignore Companies" that are not a good fit for your services.
Job Redundancy Control: Limits the number of jobs collected per company, preventing overload and focusing on diverse opportunities.
Keyword Exclusion: Automatically skips jobs related to specific areas (e.g., "government," "clearance") if they don't align with your business model.

💡 How It Works (Simplified for Business Leaders)
Configuration (Google Sheet): You define your target job search URLs (e.g., "Indeed search for 'Software Engineer' in 'New York'"), set your AI matching criteria (your "company resume" and what kind of projects you're looking for), and specify any companies to prioritize or ignore.
Automated Scanning (Indeed): The system launches multiple, "stealthy" browsers that visit these URLs, appearing as real users.
AI Qualification: Each job description found is sent to our AI engine. The AI instantly assesses how well that job's requirements align with your defined services/expertise, generating a "matching percentage."
Smart Filtering: Only jobs that meet your minimum matching percentage and other criteria (e.g., not from ignored companies) are selected.
Data Organization: The details of these qualified projects (company, title, description, your matching score, etc.) are then structured and saved.
Real-time Reporting (Google Sheets): The qualified leads are automatically uploaded to dedicated sheets in your Google Workbook, ready for your sales team to review, prioritize, and pursue.
Continuous Cycle: The process repeats, ensuring your team always has a fresh, qualified pipeline.

📈 Transform Your Business Development

Project Acquirer AI is more than a tool; it's a strategic advantage. Empower your sales and business development teams to:
Generate more qualified leads in less time.
Focus on high-value conversations, not manual data entry.
Proactively pursue projects that perfectly fit your capabilities.
Scale your project acquisition efforts without scaling your headcount.
Outmaneuver competitors who are still doing things the old way.
🛠️ Getting Started (For Technical Users)
To get Project Acquirer AI up and running, follow these steps:
Prerequisites
Python 3.8+
pip package installer
Google Cloud Project with Google Sheets API enabled (for gspread and google.oauth2)
2Captcha API Key (for Cloudflare bypass)
Gemini API Key or Groq API Key (for AI matching)
Indeed accounts (as JSON cookie files) and proxies (as proxies.txt) for optimal stealth and performance.
Installation
Clone the Repository:
git clone https://github.com/yourusername/project-acquirer-ai.git
cd project-acquirer-ai
Install Dependencies:
pip install -r requirements.txt
Set up Environment Variables:
Create a .env file in the root directory and add your API keys and email configuration:

GEMIMI_API_KEY="YOUR_GEMINI_API_KEY"
# OR
GROQ_API_KEY="YOUR_GROQ_API_KEY"

2CAPTCHA_API_KEY="YOUR_2CAPTCHA_API_KEY"

EMAIL_SENDER="your_email@example.com"
EMAIL_PASSWORD="your_email_app_password"
EMAIL_RECIPIENT="recipient_email@example.com"
SMTP_SERVER="smtp.example.com" # e.g., smtp.gmail.com
SMTP_PORT="587"
Google Sheets Credentials:
Create a Google Cloud Platform project.
Enable the Google Sheets API.
Create a Service Account and download its JSON key file.
Rename this file to gs_credentials.json and place it in the utils/ directory.
Share your configuration and output Google Workbooks with the service account's email address.
Configure config_input.py and Google Sheet:
The primary configuration is managed via a Google Sheet. The config_input.py file points to a specific Google Sheet by key. Update the client.open_by_key("YOUR_CONFIG_SHEET_ID") in config_input.py to link to your custom configuration sheet.
Create your Configuration Google Sheet:
"Settings" Tab:
CONCURRENT__SIZE: Number of concurrent browser instances.
MATCHING_PERCENTAGE: Minimum AI matching score for a job to be considered.
LEAVE_BLANK_COLLS: Number of blank columns to include in the output (for manual notes).
AI_PROMPT: Crucial! Describe your company's services and target projects. (e.g., "Our company specializes in full-stack Python development for SaaS products, cloud infrastructure migration, and DevOps consulting. We are looking for projects requiring expertise in Django, AWS, Kubernetes, and API integrations.")
RESUME: Crucial! Provide a text version of your company's "master resume" or capabilities statement, listing technologies, industries, and achievements.
PER_COMPANY_JOBS: Max number of jobs to collect per company.
PROCESS_BATCH_SIZE: How many jobs to send to AI for matching at once.
CSV_FILES: Comma-separated names for your output CSVs (e.g., Easy_applies,CS_applies,Confirmation_applies). These will also be your Google Sheet tab names.
WORKBOOK_ID: The ID of the Google Workbook where results will be uploaded.
"JobUrls" Tab: A list of Indeed search URLs (one per row).
"ConfirmationCompanies" Tab: Companies to prioritize (one per row).
"IgnoreCompanies" Tab: Companies to ignore (one per row).
Indeed Accounts and Proxies:
Place Indeed account cookie JSON files in the utils/accounts/ directory.
Create a utils/proxies.txt file (one proxy per line: IP:PORT:USERNAME:PASSWORD).
Fingerprints: The system comes with pre-loaded fingerprints in utils/fingerprints/. You can add more if desired.
Usage
To run the scraper:

python main.py
The scraper will run, outputting logs to the console and logs/spider.log. Qualified leads will be saved to CSVs in the output/ folder and then uploaded to your specified Google Sheets. Debugging screenshots will be saved in debugging_screenshots/ and sent via email upon completion.
🤝 Contributing
We welcome contributions! If you have suggestions for improvements, new features, or bug fixes, please open an issue or submit a pull request.
📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
# CareerFlow
# CareerFlow
