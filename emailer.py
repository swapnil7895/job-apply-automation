import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import logging
from typing import Optional, Dict, Any
import database

logger = logging.getLogger(__name__)

def send_email(subject: str, body: str, attachment_path: Optional[str] = None) -> bool:
    """Sends an email using the configured SMTP settings."""
    settings = database.get_email_settings()
    if not settings:
        logger.error("Email settings not configured.")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = settings['sender_email']
        receiver = settings.get('receiver_email')
        msg['To'] = receiver if receiver else settings['sender_email']
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                msg.attach(part)
        
        # Connect to SMTP server
        port = int(settings['smtp_port'])
        if port == 465:
            server = smtplib.SMTP_SSL(settings['smtp_server'], port)
        else:
            server = smtplib.SMTP(settings['smtp_server'], port)
            server.starttls()
            
        server.login(settings['sender_email'], settings['sender_password'])
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email sent successfully: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def test_email_configuration(settings: Dict[str, Any]) -> tuple[bool, str]:
    """Tests the provided SMTP settings without saving them."""
    try:
        # Use a very short timeout for testing
        port = int(settings['smtp_port'])
        if port == 465:
            server = smtplib.SMTP_SSL(settings['smtp_server'], port, timeout=10)
        else:
            server = smtplib.SMTP(settings['smtp_server'], port, timeout=10)
            server.starttls()
            
        server.login(settings['sender_email'], settings['sender_password'])
        
        # Send a quick test email
        msg = MIMEMultipart()
        msg['From'] = settings['sender_email']
        receiver = settings.get('receiver_email')
        msg['To'] = receiver if receiver else settings['sender_email']
        msg['Subject'] = "Job Apply Automation - Test Email"
        msg.attach(MIMEText("<p>Your email configuration is working perfectly!</p>", 'html'))
        
        server.send_message(msg)
        server.quit()
        return True, "Connection successful and test email sent!"
    except smtplib.SMTPAuthenticationError:
        return False, "Authentication failed. Check your email and App Password."
    except Exception as e:
        return False, f"Failed to connect: {str(e)}"
