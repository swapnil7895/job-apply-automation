# AutoApply Pro 🚀

AutoApply Pro is a fully automated, headless job application bot for **LinkedIn** and **Naukri**. It features a beautiful, local web interface where you can configure search criteria, answer AI-driven application questions, and schedule daily job-hunting runs completely on autopilot!

## ✨ Features
- **Multi-Platform**: Supports applying to jobs on LinkedIn (Easy Apply) and Naukri.
- **Smart Answers**: Uses Gemini AI (Intent Engine) to intelligently answer custom employer questions based on your skills profile.
- **Background Scheduling**: Set it up to run in the background (headless) daily at a specific time.
- **PDF Reporting**: Generates beautiful PDF reports of all the jobs you successfully applied to.
- **Persistent Sessions**: Log in once, and the app will remember your session for future runs.
- **Local Web Dashboard**: A sleek, dark-mode GUI to manage your automation.

## 🚀 Getting Started (Windows)

The easiest way to get started is to use the provided setup script. You do not need to be a developer to run this!

### Prerequisites
- You must have **Python 3.10+** installed on your computer.

### Installation & Running
1. Clone or download this repository to your local machine.
2. Double-click the `start.bat` file.
   - *On the very first run, it will automatically set up a virtual environment, install all the required dependencies, and download the Chromium browser used for automation.*
3. Open your browser and navigate to: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## 🛠️ Initial Setup Instructions
1. **API Keys**: You will need a Gemini API Key to use the Intent Engine. Create a `.env` file in the root directory and add: `GEMINI_API_KEY=your_key_here`.
2. **Login Manually**: On the web dashboard, click **"Login Manually"** for both LinkedIn and Naukri. A browser will pop up. Log into your accounts (solve any CAPTCHAs). Close the browser when done. The app will save your session!
3. **Configure & Start**: Set your filters, save your configuration, and hit **Start Automation**!

## ⚠️ Disclaimer
This tool is built for personal use to streamline the job search process. Use it responsibly and respect the terms of service of the respective platforms. Overuse or aggressive automation limits may result in temporary bans on your accounts. We recommend scheduling runs for no more than 25-50 applications a day.

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the issues page.
