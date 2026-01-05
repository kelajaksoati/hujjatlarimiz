from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import os

# ... (sizning mavjud add_watermark va rename_file kodlaringiz)

def create_lesson_template(teacher_name, subject, grade):
    """Yangi Word shablonini noldan yaratish"""
    try:
        doc = Document()
        
        # Sarlavha
        title = doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title.add_run(f"{subject.upper()} FANIDAN DARS ISHLANMASI")
        run.bold = True
        run.font.size = Pt(14)

        # Ma'lumotlar
        doc.add_paragraph(f"\nO'qituvchi: {teacher_name}")
        doc.add_paragraph(f"Sinf: {grade}")
        doc.add_paragraph(f"Mavzu: __________________________")
        
        # Bosqichlar jadvali
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Dars bosqichi'
        hdr_cells[1].text = 'Mazmuni'

        file_name = f"shablon_{teacher_name}.docx"
        doc.save(file_name)
        return file_name
    except Exception as e:
        print(f"Shablon yaratishda xato: {e}")
        return None
