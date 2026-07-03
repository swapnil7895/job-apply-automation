# utils.py
import json
import logging
from datetime import datetime

def setup_logger():
    """Sets up a logger that outputs to both a timestamped file and the console."""
    logger = logging.getLogger("LinkedinAutomation")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if setup is called multiple times
    if logger.handlers:
        return logger

    # Create timestamped filename
    timestamp = ""
    log_filename = f"run_{timestamp}.log"
    
    # Format for the logs
    log_format = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # File Handler (Writes to the timestamped log file)
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)

    # Console Handler (Outputs to terminal)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)

    # Attach handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Initialize the shared logger instance
logger = setup_logger()

def load_config():
    """Loads all configuration from config.json"""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("config.json file not found! Please create it in the same directory.")
        return {}