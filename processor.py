from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

def add_watermark(file_path, watermark_text):
    """Word fayliga avtomatik muhr va footer qo'shish"""
    try:
        if file_path.endswith('.docx'):
            doc = Document(file_path)
            for section in doc.sections:
                footer = section.footer
                # Footer mavjudligini tekshirish yoki yaratish
                p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                # Eski footer matnini o'chirib yangisini yozish (ixtiyoriy)
                p.clear() 
                run = p.add_run(f"Manba: {watermark_text} | @ish_reja_uz")
                run.font.size = Pt(9)
                run.italic = True
            
            doc.save(file_path)
            return True
    except Exception as e:
        print(f"Watermark hatosi: {e}")
    return False

def create_template(file_name, teacher_name, subject):
    """Yangi dars ishlanmasi shabloni yaratish"""
    try:
        doc = Document()
        # Sarlavha
        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title.add_run(f"{subject.upper()} FANIDAN DARS ISHLANMASI")
        run.bold = True
        run.font.size = Pt(14)

        # O'qituvchi haqida ma'lumot
        doc.add_paragraph(f"\nO'qituvchi: {teacher_name}")
        doc.add_paragraph(f"Mavzu: __________________________")
        doc.add_paragraph(f"Sana: ___ / ___ / 2026-yil")
        
        # Jadval yaratish (Dars bosqichlari uchun)
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Bosqich'
        hdr_cells[1].text = 'Mazmuni'

        save_path = f"templates/{file_name}.docx"
        os.makedirs("templates", exist_ok=True)
        doc.save(save_path)
        return save_path
    except Exception as e:
        print(f"Shablon yaratish hatosi: {e}")
        return None

def rename_file(file_path, username):
    """Fayl nomiga kanal userini qo'shish"""
    try:
        directory = os.path.dirname(file_path)
        old_name = os.path.basename(file_path)
        # Fayl nomidagi bo'shliqlarni underscore bilan almashtirish (xavfsizlik uchun)
        clean_name = old_name.replace(" ", "_")
        new_name = f"@{username}_{clean_name}"
        new_path = os.path.join(directory, new_name)
        os.rename(file_path, new_path)
        return new_path, new_name
    except Exception as e:
        print(f"Nom o'zgartirish hatosi: {e}")
        return file_path, os.path.basename(file_path)
