from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

def add_watermark(file_path, watermark_text):
    """
    Word fayliga avtomatik muhr (footer) qo'shish funksiyasi.
    """
    try:
        if file_path.endswith('.docx'):
            doc = Document(file_path)
            for section in doc.sections:
                footer = section.footer
                # Footer ichidagi paragrafni olish yoki yaratish
                p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                
                # Mavjud matnni tozalab, yangi muhrni yozish
                p.clear()
                run = p.add_run(f"Manba: {watermark_text} | @ish_reja_uz")
                run.font.size = Pt(9)
                run.italic = True
            
            doc.save(file_path)
            return True
    except Exception as e:
        print(f"DEBUG (Watermark xatosi): {e}")
    return False

def rename_file(file_path, username):
    """
    Fayl nomiga kanal userini qo'shish funksiyasi.
    """
    try:
        directory = os.path.dirname(file_path)
        old_name = os.path.basename(file_path)
        # Fayl nomidagi bo'shliqlarni tozalash
        clean_name = old_name.replace(" ", "_")
        new_name = f"@{username}_{clean_name}"
        new_path = os.path.join(directory, new_name)
        
        os.rename(file_path, new_path)
        return new_path, new_name
    except Exception as e:
        print(f"DEBUG (Nom o'zgartirish xatosi): {e}")
        return file_path, os.path.basename(file_path)

def create_lesson_template(teacher_name, subject, grade):
    """
    Noldan yangi dars ishlanmasi shablonini (Word) yaratish funksiyasi.
    """
    try:
        doc = Document()
        
        # 1. Sarlavha qismi
        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title.add_run(f"{subject.upper()} FANIDAN DARS ISHLANMASI")
        run.bold = True
        run.font.size = Pt(14)

        # 2. O'qituvchi ma'lumotlari
        info = doc.add_paragraph()
        info.add_run(f"\nO'qituvchi: ").bold = True
        info.add_run(f"{teacher_name}")
        
        info.add_run(f"\nSinf: ").bold = True
        info.add_run(f"{grade}")
        
        info.add_run(f"\nMavzu: _________________________________").bold = True
        info.add_run(f"\nSana: ____ / ____ / 2026-yil")

        # 3. Dars bosqichlari uchun jadval
        doc.add_paragraph("\nDarsning borishi:").bold = True
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Bosqich nomi'
        hdr_cells[1].text = 'Metodik mazmuni'

        # Standart qatorlar qo'shish
        steps = ["Tashkiliy qism", "Uy vazifasini tekshirish", "Yangi mavzu bayoni", "Mustahkamlash"]
        for step in steps:
            row_cells = table.add_row().cells
            row_cells[0].text = step
            row_cells[1].text = ""

        # 4. Saqlash
        file_name = f"shablon_{teacher_name.replace(' ', '_')}.docx"
        doc.save(file_name)
        return file_name
    except Exception as e:
        print(f"DEBUG (Shablon yaratish xatosi): {e}")
        return None
