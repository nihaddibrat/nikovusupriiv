FROM python:3.11-slim

# Sistem paketləri
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# yt-dlp yüklə
RUN wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/local/bin/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

# Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App files
COPY . .

# Port
ENV PORT=10000
EXPOSE 10000

# Run
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
