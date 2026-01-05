# 1. Pythonning eng barqaror va yengil versiyasini tanlaymiz
FROM python:3.10-slim

# 2. Muhit o'zgaruvchilarini sozlash (Python xatolarni darhol chiqarishi uchun)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Ishchi katalogni belgilash
WORKDIR /app

# 4. Tizim kutubxonalarini yangilash (Docker build vaqtida kerak bo'lishi mumkin)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 5. Avval requirements faylini nusxalaymiz (Keshdan unumli foydalanish uchun)
COPY requirements.txt .

# 6. Kutubxonalarni o'rnatamiz
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 7. Loyihaning barcha fayllarini nusxalash
COPY . .

# 8. Render kutadigan portni tashqariga ochish
# Eslatman: main.py ichida ham 0.0.0.0:10000 ishlatilgan bo'lishi shart
EXPOSE 10000

# 9. Botni ishga tushirish
CMD ["python", "main.py"]
