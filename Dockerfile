# Force platform to AMD64 to match Chrome & Chromedriver architecture
FROM --platform=linux/amd64 python:3.9-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV DOCKER_CONTAINER=true
ENV CHROME_VERSION=135.0.7049.95

# Install required system dependencies
RUN apt-get update && apt-get install -y \
    wget gnupg curl unzip xvfb x11vnc xterm \
    libxi6 libgconf-2-4 libexif-dev \
    fonts-liberation libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 \
    libgtk-3-0 libnspr4 libnss3 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libxss1 libxtst6 \
    libgbm1 libjpeg-dev libpng-dev libxext6 libx11-xcb1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for Testing (v135)
RUN mkdir -p /opt/chrome \
    && wget -q https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip \
    && unzip chrome-linux64.zip \
    && mv chrome-linux64/* /opt/chrome/ \
    && chmod +x /opt/chrome/chrome \
    && ln -s /opt/chrome/chrome /usr/bin/google-chrome \
    && rm -rf chrome-linux64.zip chrome-linux64

# Install matching Chromedriver
RUN wget -q https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip \
    && unzip chromedriver-linux64.zip \
    && mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && ln -s /usr/local/bin/chromedriver /usr/bin/chromedriver \
    && rm -rf chromedriver-linux64.zip chromedriver-linux64

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create required directories
RUN mkdir -p /app/downloads /app/merged_properties /app/tmp \
    && chmod -R 777 /app/downloads /app/merged_properties /app/tmp

# Copy app source
COPY . .

# Expose app port
EXPOSE 8000

# Start Flask app via Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
