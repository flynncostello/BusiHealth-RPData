# --- FILE: Dockerfile ---
FROM python:3.9-slim-bullseye

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    DOCKER_CONTAINER=true

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget curl unzip gnupg xvfb x11vnc xterm \
    libxi6 libgconf-2-4 libexif-dev \
    fonts-liberation libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 \
    libgtk-3-0 libnspr4 libnss3 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libxss1 libxtst6 \
    libgbm1 libjpeg-dev libpng-dev libxext6 libx11-xcb1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/downloads /app/merged_properties /app/tmp \
    && chmod -R 777 /app/downloads /app/merged_properties /app/tmp

# Copy Chrome install script
COPY install_chrome.sh /app/install_chrome.sh
RUN chmod +x /app/install_chrome.sh && /app/install_chrome.sh

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]