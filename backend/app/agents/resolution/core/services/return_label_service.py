from fpdf import FPDF
import os
from fastapi import Request

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 
LABEL_DIR = os.path.join(BASE_DIR, "../../static/labels")
os.makedirs(LABEL_DIR, exist_ok=True)  

def generate_return_label(
    order_id: str,
    product: str = None,
    size: int = None,
    message: str = None,
    request: Request = None
) -> str:
    file_name = f"return_label_{order_id}.pdf"
    file_path = os.path.join(LABEL_DIR, file_name)

    # Use A4, but we'll focus the design in a center block
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    # --- HEADER SECTION ---
    # Light Gray Header Background
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, 10, 190, 25, 'F')
    
    pdf.set_y(15)
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 10, "RETURN / EXCHANGE AUTHORIZATION", ln=True, align="C")
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5, "Please include this document inside or attached to your package.", ln=True, align="C")
    pdf.ln(15)

    # --- ORDER DETAILS SECTION (Table Style) ---
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "1. ORDER INFORMATION", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y()) # Horizontal divider
    pdf.ln(3)

    # Helper function for table rows within the function
    def add_row(label, value):
        pdf.set_font("Arial", 'B', 11)
        pdf.set_fill_color(250, 250, 250)
        pdf.cell(45, 10, f"  {label}", border=1, fill=True)
        pdf.set_font("Arial", '', 11)
        pdf.cell(145, 10, f"  {value}", border=1, ln=True)

    add_row("Order ID", f"#{order_id}")
    if product:
        add_row("Product Name", product)
    if size:
        add_row("Product Size", str(size))
    
    
    pdf.ln(10)

    # --- INSTRUCTIONS SECTION ---
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "2. RETURN INSTRUCTIONS", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    pdf.set_font("Arial", '', 11)
    if message:
        pdf.multi_cell(0, 7, message)
    else:
        # Professional Bullet Points
        instructions = [
            "- PACKING: Ensure the product is in its original box with all tags attached.",
            "- LABELING: Securely tape this label to the outside of the shipping box.",
            "- HANDOVER: Give this package to our authorized delivery agent upon arrival.",
            "- INSPECTION: We will ship your replacement after a quality check (approx. 2-3 days)."
        ]
        for line in instructions:
            pdf.cell(0, 8, line, ln=True)

    # --- FOOTER ---
    pdf.set_y(-50)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "Need Help?", ln=True, align="C")
    
    pdf.set_font("Arial", 'I', 10)
    pdf.set_text_color(100, 100, 100)
    footer_text = (
        "Thank you for shopping with us! If you have any questions,\n"
        "please visit our help center or contact customer support."
    )
    pdf.multi_cell(0, 6, footer_text, align="C")

    # Save PDF
    pdf.output(file_path)

    # Return URL for FastAPI
    if request:
        return f"{request.base_url}labels/{file_name}"
    else:
        return file_name