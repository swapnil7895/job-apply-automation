import os
from datetime import datetime
from fpdf import FPDF

def generate_pdf_report(platform: str, job_records: list) -> str:
    """Generates a PDF report of job application outcomes."""
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = os.path.join(reports_dir, f"{platform}_execution_report_{timestamp}.pdf")
    
    # Calculate stats
    total = len(job_records)
    applied = sum(1 for j in job_records if j.get("status") == "Applied")
    ignored = sum(1 for j in job_records if j.get("status") == "Ignored")
    failed = sum(1 for j in job_records if j.get("status") == "Failed")
    
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, f"Execution Report - {platform.capitalize()} Automation", ln=True, align="C")
    
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")
    pdf.ln(10)
    
    # Summary Stats
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "Summary Statistics", ln=True)
    
    pdf.set_font("helvetica", "", 12)
    pdf.cell(0, 8, f"Total Jobs Processed: {total}", ln=True)
    pdf.cell(0, 8, f"Successfully Applied: {applied}", ln=True)
    pdf.cell(0, 8, f"Ignored/Skipped: {ignored}", ln=True)
    pdf.cell(0, 8, f"Failed/Errors: {failed}", ln=True)
    pdf.ln(10)
    
    # Detailed Table Header
    pdf.set_font("helvetica", "B", 12)
    # Using cell widths: Title 90, Status 30, Reason 70
    pdf.cell(90, 10, "Job Title", border=1)
    pdf.cell(30, 10, "Status", border=1)
    pdf.cell(70, 10, "Reason / Detail", border=1, ln=True)
    
    # Table Rows
    pdf.set_font("helvetica", "", 10)
    for record in job_records:
        # Sanitize text to avoid encoding issues with FPDF
        title = record.get("title", "Unknown").encode('latin-1', 'replace').decode('latin-1')
        status = record.get("status", "Unknown").encode('latin-1', 'replace').decode('latin-1')
        reason = record.get("reason", "").encode('latin-1', 'replace').decode('latin-1')
        
        # truncate strings if they are too long
        title = (title[:40] + '...') if len(title) > 40 else title
        reason = (reason[:35] + '...') if len(reason) > 35 else reason
        
        pdf.cell(90, 8, title, border=1)
        pdf.cell(30, 8, status, border=1)
        pdf.cell(70, 8, reason, border=1, ln=True)
        
    pdf.output(pdf_filename)
    return pdf_filename
