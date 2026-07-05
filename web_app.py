import json
import os
import sys
import subprocess
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

import database
import scheduler

database.init_db()

app = FastAPI(title="Job Apply Automation GUI")

# Serve the static directory
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Keep track of running processes (basic implementation)
active_processes = {}

@app.on_event("startup")
async def startup_event():
    scheduler.start_scheduler()

class ConfigUpdate(BaseModel):
    config: Dict[str, Any]

class EmailConfig(BaseModel):
    smtp_server: str
    smtp_port: int
    sender_email: str
    sender_password: str
    receiver_email: Optional[str] = None

class ScheduleCreate(BaseModel):
    platform: str
    cron_time: str
    headless: bool = True

class ScheduleToggle(BaseModel):
    is_active: int

def get_config_path(platform: str) -> str:
    if platform == "linkedin":
        return "config.json"
    elif platform == "naukri":
        return "naukri_config.json"
    return ""

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.get("/api/schedules")
def get_schedules():
    return database.get_all_schedules()

@app.post("/api/schedules")
def create_schedule(sch: ScheduleCreate):
    headless_int = 1 if sch.headless else 0
    success = database.add_schedule(sch.platform, sch.cron_time, headless_int)
    if success:
        scheduler.load_schedules()
        return {"message": "Schedule created"}
    return JSONResponse(status_code=500, content={"error": "Failed to create schedule"})

@app.put("/api/schedules/{schedule_id}/toggle")
def toggle_schedule(schedule_id: int, toggle: ScheduleToggle):
    success = database.toggle_schedule(schedule_id, toggle.is_active)
    if success:
        scheduler.load_schedules()
        return {"message": "Schedule toggled"}
    return JSONResponse(status_code=500, content={"error": "Failed to toggle schedule"})

@app.delete("/api/schedules/{schedule_id}")
def delete_schedule(schedule_id: int):
    success = database.delete_schedule(schedule_id)
    if success:
        scheduler.remove_job_from_scheduler(schedule_id)
        return {"message": "Schedule deleted"}
    return JSONResponse(status_code=500, content={"error": "Failed to delete schedule"})

@app.get("/api/config/{platform}")
def get_config(platform: str):
    path = get_config_path(platform)
    if not path or not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "Config not found"})
    with open(path, "r") as f:
        return json.load(f)

@app.post("/api/config/{platform}")
def update_config(platform: str, update: ConfigUpdate):
    path = get_config_path(platform)
    if not path:
        return JSONResponse(status_code=400, content={"error": "Invalid platform"})
    with open(path, "w") as f:
        json.dump(update.config, f, indent=4)
    return {"message": "Config updated successfully"}

@app.get("/api/email/config")
def get_email_config():
    settings = database.get_email_settings()
    if not settings:
        return {"configured": False}
    return {
        "configured": True,
        "smtp_server": settings.get("smtp_server"),
        "smtp_port": settings.get("smtp_port"),
        "sender_email": settings.get("sender_email"),
        "receiver_email": settings.get("receiver_email"),
        # Never return password
    }

@app.post("/api/email/config")
def save_email_config(config: EmailConfig):
    success = database.save_email_settings(
        config.smtp_server, 
        config.smtp_port, 
        config.sender_email, 
        config.sender_password,
        config.receiver_email
    )
    if success:
        return {"message": "Email settings saved successfully"}
    return JSONResponse(status_code=500, content={"error": "Failed to save email settings"})

@app.post("/api/email/test")
def test_email_config(config: EmailConfig):
    import emailer
    settings_dict = {
        "smtp_server": config.smtp_server,
        "smtp_port": config.smtp_port,
        "sender_email": config.sender_email,
        "sender_password": config.sender_password,
        "receiver_email": config.receiver_email
    }
    success, message = emailer.test_email_configuration(settings_dict)
    if success:
        return {"message": message}
    return JSONResponse(status_code=400, content={"error": message})

@app.post("/api/start/{platform}")
def start_automation(platform: str, headless: bool = False):
    if platform not in ["linkedin", "naukri"]:
        return JSONResponse(status_code=400, content={"error": "Invalid platform"})
    
    if active_processes.get(platform) and active_processes[platform].poll() is None:
        return JSONResponse(status_code=400, content={"error": "Process already running"})

    cmd = [sys.executable, "main.py", "--platform", platform]
    if headless:
        cmd.append("--headless")
    
    try:
        process = subprocess.Popen(cmd)
        active_processes[platform] = process
        return {"message": f"Started {platform} automation", "pid": process.pid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/login/status/{platform}")
def check_login_status(platform: str):
    if platform not in ["linkedin", "naukri"]:
        return JSONResponse(status_code=400, content={"error": "Invalid platform"})
    
    cmd = [sys.executable, "main.py", "--platform", platform, "--action", "check_login", "--headless"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        # Expected output format from main.py: LOGIN_STATUS:SUCCESS|UserName or LOGIN_STATUS:FAILED
        for line in result.stdout.split('\n'):
            if line.startswith('LOGIN_STATUS:'):
                status_str = line.split(':', 1)[1].strip()
                user_name = ""
                if '|' in status_str:
                    parts = status_str.split('|', 1)
                    status_str = parts[0]
                    user_name = parts[1]
                return {"logged_in": status_str.upper() == 'SUCCESS', "user_name": user_name}
        return {"logged_in": False, "user_name": ""}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/logout/{platform}")
def logout_platform(platform: str):
    if platform not in ["linkedin", "naukri"]:
        return JSONResponse(status_code=400, content={"error": "Invalid platform"})
    
    cmd = [sys.executable, "main.py", "--platform", platform, "--action", "logout", "--headless"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return {"message": f"Logged out from {platform} successfully"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/login/manual/{platform}")
def manual_login(platform: str):
    if platform not in ["linkedin", "naukri"]:
        return JSONResponse(status_code=400, content={"error": "Invalid platform"})
    
    if active_processes.get(platform) and active_processes[platform].poll() is None:
        return JSONResponse(status_code=400, content={"error": "Process already running"})
        
    # Not headless because user needs to see it
    cmd = [sys.executable, "main.py", "--platform", platform, "--action", "manual_login"]
    try:
        process = subprocess.Popen(cmd)
        active_processes[platform] = process
        return {"message": f"Started manual login for {platform}"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/status/{platform}")
def get_status(platform: str):
    is_running = False
    if active_processes.get(platform):
        if active_processes[platform].poll() is None:
            is_running = True

    # Get latest log file
    logs_dir = "logs"
    latest_logs = []
    limit_reached = False
    
    if os.path.exists(logs_dir):
        log_files = [f for f in os.listdir(logs_dir) if f.startswith(platform) and f.endswith(".log")]
        if log_files:
            log_files.sort(key=lambda x: os.path.getmtime(os.path.join(logs_dir, x)), reverse=True)
            latest_log_path = os.path.join(logs_dir, log_files[0])
            with open(latest_log_path, "r") as f:
                lines = f.readlines()
                latest_logs = [line.strip() for line in lines[-20:]]

            # Check for limit reached persistently across today's logs
            import datetime
            today = datetime.date.today()
            for log_file in log_files:
                log_path = os.path.join(logs_dir, log_file)
                # Only check today's logs
                if datetime.date.fromtimestamp(os.path.getmtime(log_path)) != today:
                    continue
                
                try:
                    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        
                        # We are reading from newest to oldest file. 
                        # If a newer file had a successful application, the limit must have reset.
                        if "Submitting application..." in content or "Closing post-submission popup" in content:
                            limit_reached = False
                            break
                            
                        # If we hit the limit reached message first, then limit is indeed reached today
                        if "Easy Apply limit reached" in content:
                            limit_reached = True
                            break
                except:
                    pass

    return {
        "running": is_running,
        "latest_logs": latest_logs,
        "limit_reached": limit_reached
    }

class DeleteRunsRequest(BaseModel):
    run_ids: List[int]

@app.get("/api/runs/{platform}")
def get_runs(platform: str):
    runs = database.get_runs(platform)
    return {"runs": runs}

@app.delete("/api/runs")
def delete_runs(req: DeleteRunsRequest):
    deleted_count = database.delete_runs(req.run_ids)
    return {"success": True, "deleted": deleted_count}

@app.get("/api/reports/{filename}")
def download_report(filename: str):
    file_path = os.path.join("reports", filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    return JSONResponse(status_code=404, content={"error": "Report not found"})
