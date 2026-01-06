# 1-qadam: Eng yengil Python versiyasini tanlash
FROM python:3.10-slim

# 2-qadam: Tizim kutubxonalarini yangilash (PDF va Excel amallari uchun kerak bo'lishi mumkin)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 3-qadam: Ishchi katalogni belgilash
WORKDIR /app

# 4-qadam: Kutubxonalar ro'yxatini nusxalash va o'rnatish
# (Nusxalashni requirements dan boshlash keshdan samarali foydalanishga yordam beradi)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5-qadam: Barcha loyiha fayllarini nusxalash
COPY . .

# 6-qadam: Render portini ochish
EXPOSE 10000

# 7-qadam: Botni ishga tushirish
CMD ["python", "main.py"]
