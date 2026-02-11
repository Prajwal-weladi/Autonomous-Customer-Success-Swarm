from fpdf import FPDF
import os
from fastapi import Request

# Set relative path to labels folder inside the repo
# This works on any machine, no absolute local paths
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
    """
    Generates a professional return label PDF with detailed information
    and returns the URL path to access it via FastAPI.
    
    Args:
        order_id (str): Unique order ID
        product (str): Name of the product
        size (int): Size of the product
        message (str): Custom message for the return/exchange instructions
        request (Request): FastAPI Request object to generate full URL
    
    Returns:
        str: URL to access the generated PDF
    """
    file_name = f"return_label_{order_id}.pdf"
    file_path = os.path.join(LABEL_DIR, file_name)

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()

    # Title
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 15, "RETURN / EXCHANGE LABEL", ln=True, align="C")
    pdf.ln(10)

    # Order Details Box
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Order Details:", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Order ID: {order_id}", ln=True)
    if product:
        pdf.cell(0, 8, f"Product: {product}", ln=True)
    if size:
        pdf.cell(0, 8, f"Size: {size}", ln=True)
    
    pdf.ln(5)

    # Instructions Box
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Instructions:", ln=True)
    pdf.set_font("Arial", '', 12)
    if message:
        pdf.multi_cell(0, 8, message)
    else:
        pdf.multi_cell(
            0, 8,
            "Please attach this label securely to the product package.\n"
            "Present this label to your delivery partner who will collect the item for exchange.\n"
            "Your replacement product will be shipped once the returned item is received and inspected.\n"
            "Keep this label safe until the exchange is completed."
        )
    
    pdf.ln(10)

    # Footer / Thank you note
    pdf.set_font("Arial", 'I', 11)
    pdf.multi_cell(
        0, 6,
        "Thank you for shopping with us!\n"
        "For any questions, please contact our customer service center."
    )

    # Save PDF
    pdf.output(file_path)

    # Return URL for FastAPI
    if request:
        # full URL accessible from browser
        return f"{request.base_url}labels/{file_name}"
    else:
        # fallback: return relative path
        return file_name

