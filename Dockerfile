# Use official Python base image with AMD64 architecture
FROM python:3.9-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:99
ENV DOCKER_CONTAINER=true
ENV CHROME_VERSION="136.0.7103.92"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget gnupg curl unzip xvfb x11vnc xterm \
    libxi6 libgconf-2-4 libexif-dev \
    fonts-liberation libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 \
    libgtk-3-0 libnspr4 libnss3 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libxss1 libxtst6 \
    libgbm1 libjpeg-dev libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for Testing (v136) - Using verified URL from the availability page
RUN mkdir -p /opt/chrome \
    && wget -q https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip \
    && unzip chrome-linux64.zip \
    && mv chrome-linux64/* /opt/chrome/ \
    && chmod +x /opt/chrome/chrome \
    && ln -s /opt/chrome/chrome /usr/bin/google-chrome \
    && rm -rf chrome-linux64.zip chrome-linux64

# Install matching ChromeDriver (v136) - Using verified URL from the availability page
RUN wget -q https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip \
    && unzip chromedriver-linux64.zip \
    && mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && ln -s /usr/local/bin/chromedriver /usr/bin/chromedriver \
    && rm -rf chromedriver-linux64.zip chromedriver-linux64

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories and set permissions
RUN mkdir -p /app/downloads /app/merged_properties /app/tmp \
    && chmod -R 777 /app/downloads /app/merged_properties /app/tmp

# Copy app source code
COPY . .

# Expose the Flask app port
EXPOSE 8000

# Run using Gunicorn directly (no entrypoint.sh)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]