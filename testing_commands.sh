docker build -t rpdata-scraper:test .
docker run --rm -it --platform=linux/amd64 --shm-size=2g -p 8000:8000 rpdata-scraper:test


docker run -it --rm --platform=linux/amd64 --shm-size=2g rpdata-scraper:test bash
# Then try:
/opt/chrome/chrome --headless --disable-gpu --remote-debugging-port=9222 https://www.google.com
