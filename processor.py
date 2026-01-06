from docx import Document
import os

def create_lesson_template(name, subject, grade):
    """
    O'qituvchi ma'lumotlari asosida to'liq Word shablonini yaratadi.
    """
    # Yangi hujjat (Word) ob'ektini yaratish
    doc = Document()
    
    # Hujjat sarlavhasi
    doc.add_heading('Dars Ishlanmasi (Shablon)', 0)
    
    # O'qituvchi va dars ma'lumotlari
    doc.add_paragraph(f"O'qituvchi: {name}")
    doc.add_paragraph(f"Fan: {subject}")
    doc.add_paragraph(f"Sinf: {grade}")
    
    # Vizual ajratuvchi va to'ldirish uchun bo'limlar
    doc.add_paragraph("\n" + "_"*40)
    doc.add_paragraph("Mavzu: ________________________________")
    doc.add_paragraph("Darsning maqsadi: _______________________")
    doc.add_paragraph("Kutilayotgan natijalar: __________________")
    
    # Dars bosqichlari uchun qo'shimcha bo'sh joy
    doc.add_paragraph("Dars bosqichlari: \n1. ...\n2. ...\n3. ...")
    
    # Faylni saqlash uchun 'templates' papkasi borligini tekshirish
    if not os.path.exists("templates"):
        os.makedirs("templates")
        
    # Fayl nomi yaratish (ismdagi bo'shliqlarni '_' ga almashtirish xatolarni oldini oladi)
    file_name = f"shablon_{name.replace(' ', '_')}.docx"
    file_path = os.path.join("templates", file_name)
    
    # Hujjatni saqlash
    doc.save(file_path)
    
    return file_path
