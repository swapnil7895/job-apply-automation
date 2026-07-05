import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "automation_runs.db")

def init_db():
    """Initializes the database and creates the automation_runs table if it doesn't exist."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS automation_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    success_count INTEGER DEFAULT 0,
                    ignore_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    pdf_path TEXT,
                    email_status TEXT
                )
            ''')
            
            # Create email_settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    smtp_server TEXT NOT NULL,
                    smtp_port INTEGER NOT NULL,
                    sender_email TEXT NOT NULL,
                    sender_password TEXT NOT NULL,
                    receiver_email TEXT
                )
            ''')
            
            # Create schedules table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    cron_time TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    headless INTEGER DEFAULT 1
                )
            ''')
            
            # Migration to add headless column to schedules if it doesn't exist
            cursor.execute("PRAGMA table_info(schedules)")
            sch_cols = [col[1] for col in cursor.fetchall()]
            if 'headless' not in sch_cols and sch_cols:
                cursor.execute("ALTER TABLE schedules ADD COLUMN headless INTEGER DEFAULT 1")
            
            # Migration to add receiver_email if it doesn't exist
            cursor.execute("PRAGMA table_info(email_settings)")
            email_cols = [col[1] for col in cursor.fetchall()]
            if 'receiver_email' not in email_cols and email_cols:
                cursor.execute("ALTER TABLE email_settings ADD COLUMN receiver_email TEXT")
            
            # Migration to add email_status column if it doesn't exist
            cursor.execute("PRAGMA table_info(automation_runs)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'email_status' not in columns:
                cursor.execute("ALTER TABLE automation_runs ADD COLUMN email_status TEXT")
                
            conn.commit()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

def get_email_settings() -> Dict[str, Any]:
    """Retrieves email configuration."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM email_settings ORDER BY id DESC LIMIT 1')
            row = cursor.fetchone()
            if row:
                return dict(row)
    except Exception as e:
        logger.error(f"Error fetching email settings: {e}")
    return None

def save_email_settings(smtp_server: str, smtp_port: int, sender_email: str, sender_password: str, receiver_email: str = None) -> bool:
    """Saves email configuration."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Clear existing to maintain just one config record
            cursor.execute('DELETE FROM email_settings')
            cursor.execute('''
                INSERT INTO email_settings (smtp_server, smtp_port, sender_email, sender_password, receiver_email)
                VALUES (?, ?, ?, ?, ?)
            ''', (smtp_server, smtp_port, sender_email, sender_password, receiver_email))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving email settings: {e}")
        return False

def save_run(platform: str, status: str, success_count: int, ignore_count: int, failed_count: int, pdf_path: str = None, email_status: str = None) -> int:
    """Saves a run record to the database."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            timestamp = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO automation_runs 
                (platform, timestamp, status, success_count, ignore_count, failed_count, pdf_path, email_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (platform, timestamp, status, success_count, ignore_count, failed_count, pdf_path, email_status))
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error saving run to database: {e}")
        return -1

def get_runs(platform: str = None) -> List[Dict[str, Any]]:
    """Retrieves all runs, optionally filtered by platform, ordered by newest first."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if platform:
                cursor.execute('SELECT * FROM automation_runs WHERE platform = ? ORDER BY timestamp DESC', (platform,))
            else:
                cursor.execute('SELECT * FROM automation_runs ORDER BY timestamp DESC')
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Error fetching execution history: {e}")
        return []

def add_schedule(platform: str, cron_time: str, headless: int = 1) -> bool:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO schedules (platform, cron_time, is_active, created_at, headless) VALUES (?, ?, 1, ?, ?)",
                (platform, cron_time, datetime.now().isoformat(), headless)
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        logger.error(f"Error adding schedule: {e}")
        return False

def get_all_schedules() -> List[Dict[str, Any]]:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM schedules ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error fetching schedules: {e}")
        return []

def toggle_schedule(schedule_id: int, is_active: int) -> bool:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE schedules SET is_active = ? WHERE id = ?", (is_active, schedule_id))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logger.error(f"Error toggling schedule: {e}")
        return False

def delete_schedule(schedule_id: int) -> bool:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            conn.commit()
            return True
    except sqlite3.Error as e:
        logger.error(f"Error deleting schedule: {e}")
        return False

def delete_runs(run_ids: List[int]) -> int:
    """Deletes multiple runs from the database by ID and removes their associated PDFs."""
    if not run_ids:
        return 0
    deleted_count = 0
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Fetch PDF paths before deleting
            placeholders = ','.join(['?'] * len(run_ids))
            cursor.execute(f'SELECT pdf_path FROM automation_runs WHERE id IN ({placeholders})', run_ids)
            rows = cursor.fetchall()
            
            # Delete PDFs from disk
            for row in rows:
                pdf_path = row[0]
                if pdf_path and os.path.exists(pdf_path):
                    try:
                        os.remove(pdf_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete PDF {pdf_path}: {e}")
            
            # Delete from DB
            cursor.execute(f'DELETE FROM automation_runs WHERE id IN ({placeholders})', run_ids)
            deleted_count = cursor.rowcount
            conn.commit()
            
        return deleted_count
    except Exception as e:
        logger.error(f"Error deleting runs from database: {e}")
        return deleted_count

def update_run_email_status(run_id: int, email_status: str) -> bool:
    """Updates the email status for a specific run."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE automation_runs 
                SET email_status = ?
                WHERE id = ?
            ''', (email_status, run_id))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating run email status: {e}")
        return False
