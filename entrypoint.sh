#!/bin/bash
ARCH=$(dpkg --print-architecture)

if [ "$ARCH" = "arm64" ]; then
    export CHROME_BINARY="/usr/bin/chromium"
    export CHROMEDRIVER_PATH="/usr/bin/chromedriver"
else
    export CHROME_BINARY="/opt/chrome/chrome"
    export CHROMEDRIVER_PATH="/usr/bin/chromedriver"
fi

exec "$@"
