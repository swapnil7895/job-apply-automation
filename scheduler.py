import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import database
import subprocess
import os
import sys

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
    load_schedules()
    logger.info("Scheduler started and schedules loaded.")

def load_schedules():
    # Remove existing jobs managed by us
    for job in scheduler.get_jobs():
        if str(job.id).startswith("schedule_"):
            scheduler.remove_job(job.id)
        
    schedules = database.get_all_schedules()
    for sch in schedules:
        if sch["is_active"]:
            add_job_to_scheduler(sch)

def add_job_to_scheduler(sch):
    cron_time = sch["cron_time"]
    try:
        hour, minute = cron_time.split(":")
        job_id = f"schedule_{sch['id']}"
        scheduler.add_job(
            execute_job,
            CronTrigger(hour=int(hour), minute=int(minute)),
            args=[sch["platform"], sch.get("headless", 1)],
            id=job_id,
            replace_existing=True
        )
        logger.info(f"Added job {job_id} for {sch['platform']} at {cron_time}")
    except Exception as e:
        logger.error(f"Failed to add job {sch['id']}: {e}")

def remove_job_from_scheduler(schedule_id):
    job_id = f"schedule_{schedule_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

def execute_job(platform, headless):
    logger.info(f"Executing scheduled job for {platform} (headless: {headless})")
    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        cmd = [sys.executable, "main.py", "--platform", platform]
        if headless:
            cmd.append("--headless")
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
        )
    except Exception as e:
        logger.error(f"Error starting scheduled job for {platform}: {e}")
