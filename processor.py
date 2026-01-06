import os
import openpyxl
from openpyxl.styles import Font
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from io import BytesIO
from docx import Document

def smart_rename(filename):
    """Fayl nomini brendlash va chiroyli holatga keltirish"""
    base_name, extension = os.path.splitext(filename)
    # Belgilarni tozalash
    clean_name = base_name.replace("_", " ").replace("-", " ").strip()
    
    # BSB/CHSB bo'lsa alohida ajratish, bo'lmasa Title Case qilish
    if 'bsb' in clean_name.lower():
        clean_name = f"BSB {clean_name.upper().replace('BSB', '')}"
    else:
        clean_name = clean_name.title()
        
    return f"@ISH_REJA_UZ_{clean_name.replace(' ', '_')}{extension.lower()}"

def edit_excel(path):
    """Excelga yangi qator qo'shish va qizil rangli brend yozish"""
    try:
        wb = openpyxl.load_workbook(path)
        ws = wb.active
        # Eng tepaga yangi qator qo'shish (formulalarni pastga suradi)
        ws.insert_rows(1)
        ws['A1'] = "@ish_reja_uz kanali uchun maxsus tayyorlandi"
        ws['A1'].font = Font(bold=True, color="FF0000", size=12)
        wb.save(path)
        wb.close()
    except Exception as e:
        print(f"Excel error: {e}")
    return path

def add_pdf_watermark(path):
    """PDF sahifalari markaziga shaffof va qiyshiq watermark qo'yish"""
    try:
        reader = PdfReader(path)
        writer = PdfWriter()
        
        # Watermark (suv belgisi) qatlamini yaratish
        packet = BytesIO()
        can = canvas.Canvas(packet)
        can.setFont("Helvetica-Bold", 45)
        can.setFillGray(0.5, 0.15)  # 15% shaffoflik
        can.saveState()
        can.translate(300, 450)     # Markazga yaqinlashtirish
        can.rotate(45)              # 45 gradus burchak
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

def edit_docx(path):
    """Word hujjatining eng tepasiga brend yozuvini qo'shish"""
    try:
        doc = Document(path)
        doc.add_paragraph("@ish_reja_uz kanali uchun maxsus", style='Normal').insert_paragraph_before("@ish_reja_uz")
        doc.save(path)
    except Exception as e:
        print(f"Word error: {e}")
    return path
