import os, openpyxl
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from io import BytesIO

def smart_rename(filename):
    """Fayl nomini brendlash"""
    clean_name = filename.upper().replace("_", " ").replace("-", " ")
    return f"@ISH_REJA_UZ_{clean_name}"

def edit_excel(path):
    """Excel tahrirlash"""
    try:
        wb = openpyxl.load_workbook(path)
        ws = wb.active
        ws['A1'] = "@ish_reja_uz"
        wb.save(path)
        wb.close() # Xotirani bo'shatish
    except: pass
    return path

def add_pdf_watermark(path):
    """PDF watermark"""
    try:
        reader = PdfReader(path)
        writer = PdfWriter()
        water_buf = BytesIO()
        c = canvas.Canvas(water_buf)
        c.setFont("Helvetica", 45)
        c.setFillGray(0.5, 0.2)
        c.saveState()
        c.translate(300, 450); c.rotate(45)
        c.drawCentredString(0, 0, "@ish_reja_uz")
        c.restoreState(); c.save()
        
        water_page = PdfReader(water_buf).pages[0]
        for page in reader.pages:
            page.merge_page(water_page)
            writer.add_page(page)
        with open(path, "wb") as f: writer.write(f)
    except: pass
    return path
