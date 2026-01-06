# 1-qadam: Eng barqaror va yengil Python versiyasi
FROM python:3.10-slim

# 2-qadam: Tizim kutubxonalarini yangilash
# Bu PDF (pypdf, reportlab) va Excel (openpyxl) amallari uchun zarur
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 3-qadam: Ishchi katalogni yaratish
WORKDIR /app

# 4-qadam: Kutubxonalarni o'rnatish
# Avval requirements nusxalanadi, bu har safar "pip install" qilmaslik uchun keshdan foydalanadi
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5-qadam: Loyiha fayllarini nusxalash
COPY . .

# 6-qadam: Render uchun portni belgilash
# Render odatda 10000 portdan foydalanadi
EXPOSE 10000

# 7-qadam: Botni ishga tushirish
CMD ["python", "main.py"]
