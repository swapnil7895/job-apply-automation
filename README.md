# LinkedIn Easy Apply Automation

This project automates the process of searching and applying for jobs on LinkedIn using Playwright. It specifically targets jobs with the "Easy Apply" option and automatically fills out application forms based on your predefined configuration.

## Features

- **Automated Login**: Securely logs into your LinkedIn account.
- **Job Search**: Automatically searches for jobs (currently set to "python" by default).
- **Smart Filtering**: Applies filters for "Jobs", "Easy Apply", and "Past week".
- **Dynamic Form Filling**: Intelligently detects and fills out dynamic application form fields (e.g., experience, CTC, location, LinkedIn profile URL, yes/no questions) using the details provided in `config.json`.
- **Persistent Session**: Uses a persistent Chrome profile to maintain sessions and minimize repeated login prompts.

## Prerequisites

- Python 3.x
- [Playwright for Python](https://playwright.dev/python/)

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/swapnil7895/job-apply-automation.git
   cd job-apply-automation
   ```

2. **Install dependencies:**
   Ensure you have Playwright installed and its browsers downloaded:
   ```bash
   pip install playwright
   playwright install chromium
   ```

3. **Configure your details:**
   Update the `config.json` file with your LinkedIn credentials and professional details. This data is used to automatically fill the Easy Apply forms.
   ```json
   {
       "linkedin_username": "your_email@example.com",
       "linkedin_password": "your_password",
       "total_exp": "5",
       "linkedin_url": "https://www.linkedin.com/in/your-profile/",
       "mobile": "1234567890",
       "notice_period": "30",
       "ctc": "16.2",
       "ctc_full": "1620000",
       "expected_ctc": "23",
       "expected_ctc_full": "2300000",
       "location": "Pune"
   }
   ```
   *(Note: Ensure you do not commit your real password to version control!)*

## Usage

Run the main script to start the automation:

```bash
python job_apply.py
```

The script will launch a visible Chrome browser instance, navigate to LinkedIn, perform the search, and iterate through the job listings to submit applications.

## Current State & Notes

- The search keyword is currently hardcoded to `"python"` within `linkedin_actions.py`.
- It relies on specific DOM elements, test IDs, and XPaths which may break if LinkedIn updates its UI.
- The automation uses a specific Chrome profile directory path in `job_apply.py`. You may need to adjust the `user_data_dir` path to match your system setup.
