from fpdf import FPDF
import os
from fastapi import Request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

FONT_PATH = str(BASE_DIR.parent.parent / "fonts" / "DejaVuSans.ttf")
LABEL_DIR = str(BASE_DIR.parent.parent / "static" / "labels")

os.makedirs(LABEL_DIR, exist_ok=True)


def generate_return_label(
    order_id: str,
    product: str = None,
    size: int = None,
    message: str = None,
    request: Request = None
) -> str:

    file_name = f"return_label_{order_id}.pdf"
    file_path = os.path.join(str(LABEL_DIR), file_name)

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()

    # ✅ Unicode Font
    pdf.add_font("DejaVu", "", FONT_PATH, uni=True)
    pdf.set_font("DejaVu", size=12)

    # ---------------- HEADER ----------------
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, 10, 190, 25, 'F')

    pdf.set_y(15)
    pdf.set_font("DejaVu", size=18)
    pdf.cell(0, 10, "RETURN / EXCHANGE AUTHORIZATION", ln=True, align="C")

    pdf.set_font("DejaVu", size=10)
    pdf.cell(0, 5, "Please include this document inside your package.", ln=True, align="C")
    pdf.ln(15)

    # ---------------- ORDER INFO ----------------
    pdf.set_font("DejaVu", size=13)
    pdf.cell(0, 10, "1. ORDER INFORMATION", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    def add_row(label, value):
        pdf.set_font("DejaVu", size=11)
        pdf.cell(50, 10, f"{label}", border=1)
        pdf.cell(140, 10, f"{value}", border=1, ln=True)

    add_row("Order ID", f"#{order_id}")

    if product:
        add_row("Product Name", product)

    if size:
        add_row("Product Size", str(size))

    

    pdf.ln(10)

    # ---------------- INSTRUCTIONS ----------------
    pdf.set_font("DejaVu", size=13)
    pdf.cell(0, 10, "2. RETURN INSTRUCTIONS", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    pdf.set_font("DejaVu", size=11)

    if message:
        pdf.multi_cell(0, 7, message)
    else:
        instructions = [
            "• PACKING: Ensure product is in original box with tags.",
            "• LABELING: Attach this label outside shipping box.",
            "• HANDOVER: Give package to delivery agent.",
            "• INSPECTION: Replacement ships after quality check."
        ]
        for line in instructions:
            pdf.cell(0, 8, line, ln=True)

    pdf.ln(20)

    # ---------------- FOOTER ----------------
    pdf.set_y(-40)
    pdf.set_font("DejaVu", size=11)
    pdf.cell(0, 8, "Need Help?", ln=True, align="C")

    pdf.set_font("DejaVu", size=10)
    footer_text = (
        "Thank you for shopping with us!\n"
        "Contact support if you need assistance."
    )
    pdf.multi_cell(0, 6, footer_text, align="C")

    pdf.output(file_path)

    # Return URL for FastAPI
    if request:
        return f"{request.base_url}labels/{file_name}"
    return file_name
