import os
import openpyxl
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from io import BytesIO
from docx import Document

def smart_rename(filename):
    """Fayl nomini brendlash va tozalash"""
    # Kengaytmani ajratish
    base_name, extension = os.path.splitext(filename)
    # Belgilarni tozalash va katta harfga o'tkazish
    clean_name = base_name.upper().replace("_", " ").replace("-", " ").strip()
    return f"@ISH_REJA_UZ_{clean_name}{extension.lower()}"

def edit_excel(path):
    """Excel A1 katagiga brend yozish"""
    try:
        # data_only=False formulalarni saqlab qolish uchun
        wb = openpyxl.load_workbook(path)
        ws = wb.active
        ws['A1'] = "@ish_reja_uz"
        wb.save(path)
        wb.close()
    except Exception as e:
        print(f"Excel error: {e}")
    return path

def add_pdf_watermark(path):
    """PDF sahifalari markaziga shaffof belgi qo'yish"""
    try:
        reader = PdfReader(path)
        writer = PdfWriter()
        
        # Watermark yaratish
        packet = BytesIO()
        can = canvas.Canvas(packet)
        can.setFont("Helvetica-Bold", 40)
        can.setFillGray(0.5, 0.2) # 20% shaffoflik
        can.saveState()
        can.translate(300, 450)
        can.rotate(45)
        can.drawCentredString(0, 0, "@ish_reja_uz")
        can.restoreState()
        can.save()
        
        packet.seek(0)
        watermark_pdf = PdfReader(packet)
        watermark_page = watermark_pdf.pages[0]
        
        for page in reader.pages:
            page.merge_page(watermark_page)
            writer.add_page(page)
            
        with open(path, "wb") as f:
            writer.write(f)
    except Exception as e:
        print(f"PDF watermark error: {e}")
    return path
