# 1. Eng barqaror va yengil versiya
FROM python:3.10-slim

# 2. Python xatolarni va loglarni keshda ushlamasdan darhol chiqarishi uchun
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Ishchi papkani yaratish
WORKDIR /app

# 4. Tizim paketlarini o'rnatish (SQLite va Docx uchun kerak bo'lishi mumkin)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 5. Keshni optimallashtirish: Avval faqat requirements.txt ni ko'chiramiz
# Bu orqali agar kod o'zgarsa-yu, kutubxonalar o'zgarmasa, Render ularni qayta yuklamaydi
COPY requirements.txt .

# 6. Kutubxonalarni o'rnatish
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 7. Loyihaning qolgan barcha fayllarini ko'chirish
COPY . .

# 8. Render kutadigan port (Ixtiyoriy, lekin yaxshi amaliyot)
EXPOSE 10000

# 9. Botni ishga tushirish
CMD ["python", "main.py"]
