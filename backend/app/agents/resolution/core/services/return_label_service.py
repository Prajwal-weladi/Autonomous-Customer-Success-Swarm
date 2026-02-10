from fpdf import FPDF
import os

# Directory to save generated labels
LABEL_DIR = r"C:\Users\ACER\Desktop\GlideCloud\Customer_success_swarm\resolution_agent\static\labels"

def generate_return_label(order_id: str, product: str = None, size: int = None, message: str = None) -> str:
    """
    Generates a professional return label PDF with detailed information.
    
    Args:
        order_id (str): Unique order ID
        product (str): Name of the product
        size (int): Size of the product
        message (str): Custom message for the return/exchange instructions
    
    Returns:
        str: File name of the generated PDF
    """
    os.makedirs(LABEL_DIR, exist_ok=True)
    
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
    
    pdf.output(file_path)
    return file_name
