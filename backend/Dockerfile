# Senin tercih ettiğin gibi Python 3.12 ile başlıyoruz
FROM python:3.12-slim

# Python'un gereksiz cache dosyaları oluşturmasını ve logları geciktirmesini engelliyoruz
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# PostgreSQL bağımlılıklarını kuruyoruz (Eğer psycopg2-binary kullanmıyorsan bu şart)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Dosyaları kopyalıyoruz
COPY . .

# Entrypoint script'ine çalıştırma izni veriyoruz
RUN chmod +x docker-entrypoint.sh

# Senin eklediğin HARİKA güvenlik önlemi: Uygulamayı yetkisiz bir kullanıcı ile çalıştırmak
RUN useradd --create-home --uid 1000 kursu
USER kursu

EXPOSE 8000

# Konteyner başlarken çalışacak komutlar
ENTRYPOINT ["./docker-entrypoint.sh"]