# Job Apply Automation — LinkedIn & Naukri

Automates job searching and applying on **LinkedIn** (Easy Apply) and **Naukri**, using Playwright. A single CLI entry point lets you pick which platform to run.

## Features

### LinkedIn
- Automated login with session detection
- Searches for jobs (currently: `python` keyword)
- Applies filters: **Jobs**, **Easy Apply**, **Past week**
- Dynamically fills multi-step Easy Apply forms (CTC, experience, location, LinkedIn URL, yes/no questions)
- Handles post-submit popups and "Already Applied" skipping

### Naukri
- Automated login with session detection
- Searches jobs by keyword + location from config
- Applies the **Apply on Naukri** filter (direct apply only)
- Fills application modals dynamically (current CTC, expected CTC, experience, notice period, location)
- Handles multi-step apply modal with Next / Submit navigation

## Project Structure

```
.
├── main.py               # Unified entry point — pick platform via --platform flag
├── linkedin_actions.py   # All LinkedIn automation logic
├── naukri_actions.py     # All Naukri automation logic (isolated)
├── job_apply.py          # Legacy LinkedIn-only runner (still works standalone)
├── utils.py              # Shared logger & config loader (used by legacy runner)
├── config.json           # LinkedIn credentials & profile data  ← git-ignored
├── naukri_config.json    # Naukri credentials & profile data    ← git-ignored
└── test_xpath.py         # XPath / selector debugging scratchpad
```

## Prerequisites

- Python 3.x
- Install dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

## Configuration

### `config.json` (LinkedIn)
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

### `naukri_config.json` (Naukri)
```json
{
    "naukri_username": "your_email@example.com",
    "naukri_password": "your_password",
    "keywords": "Python Developer",
    "location": "Pune",
    "experience": "5",
    "notice_period": "30",
    "current_ctc": "16.2",
    "expected_ctc": "23",
    "resume_path": ""
}
```

> ⚠️ Both config files are in `.gitignore` — never commit real credentials.

## Usage

### Run LinkedIn automation
```bash
python main.py --platform linkedin
```

### Run Naukri automation
```bash
python main.py --platform naukri
```

### Use a custom config file
```bash
python main.py --platform naukri --config my_naukri_config.json
```

### Legacy LinkedIn-only runner (still works)
```bash
python job_apply.py
```

## Notes & Known Limitations

- The LinkedIn search keyword (`python`) is hardcoded in `linkedin_actions.py` — to be made configurable.
- Both runners use the same persistent Chrome profile (`ChromeAutomationProfile`). Adjust the `user_data_dir` path in `main.py` to match your system.
- XPath and DOM selectors are subject to break when LinkedIn / Naukri update their UI.
- If CAPTCHA or 2FA is triggered, the script pauses and asks you to log in manually.
