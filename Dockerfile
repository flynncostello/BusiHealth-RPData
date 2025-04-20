# Use an official Python runtime as a parent image
FROM python:3.9-slim-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    x11vnc \
    xinit \
    xterm \
    libxi6 \
    libgconf-2-4 \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable

# Install ChromeDriver with version matching installed Chrome
RUN CHROME_VERSION=$(google-chrome --version | cut -d ' ' -f 3 | cut -d '.' -f 1) \
    && CHROMEDRIVER_VERSION=$(curl -sS https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}) \
    && echo "Installing ChromeDriver version: ${CHROMEDRIVER_VERSION}" \
    && wget -q https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm chromedriver_linux64.zip

# Set the working directory in the container
WORKDIR /app

# Copy requirements and install Python dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for web scraping
RUN pip install undetected-chromedriver selenium xvfbwrapper

# Copy the current directory contents into the container at /app
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /app/downloads /app/merged_properties /app/tmp \
    && chmod -R 777 /app/downloads /app/merged_properties /app/tmp

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV DOCKER_CONTAINER=true
ENV WEBSITE_SITE_NAME=DockerContainer

# Expose VNC port
EXPOSE 8000 5900

# Use a shell script to start Xvfb, VNC, and the application
COPY entrypoint_vnc.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run the application
ENTRYPOINT ["/entrypoint.sh"]