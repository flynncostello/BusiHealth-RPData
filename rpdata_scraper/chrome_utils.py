# --- FILE: chrome_utils.py ---

#!/usr/bin/env python3
# Chrome utilities for web scraping with stealth & WebGL spoofing in Azure/Docker

import os
import sys
import time
import random
import logging
import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_chrome_driver(headless=True, download_dir=None):
    try:
        logger.info("Setting up Chrome driver for cloud/Docker environment...")

        is_azure = os.environ.get('WEBSITE_SITE_NAME') is not None
        is_container = is_azure or 'DOCKER_CONTAINER' in os.environ or os.path.exists('/.dockerenv')
        is_macos = platform.system() == "Darwin"

        logger.info(f"Environment detection: Azure={is_azure}, Container={is_container}, macOS={is_macos}")

        if is_container and not headless:
            logger.info("Running in container environment - forcing headless mode")
            headless = True

        logger.info(f"Using headless mode: {headless}")

        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
        options.add_argument("--window-size=1920,1080")
        
        # Initialize prefs dictionary early
        prefs = {
            "download.default_directory": download_dir if download_dir else "/tmp",
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "plugins.always_open_pdf_externally": True,
            # Additional performance preferences
            "profile.default_content_setting_values.images": 2,  # Don't load images
            "profile.default_content_setting_values.cookies": 1,  # Accept cookies
            "profile.managed_default_content_settings.javascript": 1,  # Enable JavaScript
            # Network timeouts
            "network.tcp.connect_timeout_ms": 10000  # 10 seconds
        }
        
        # Special configuration for Azure that focuses on performance and stability
        if is_azure:
            logger.info("Using Azure-specific Chrome configuration")

            # Set page load strategy to eager
            options.page_load_strategy = 'eager'
            
            # Critical for WebGL in Azure
            options.add_argument("--disable-gpu-sandbox")
            options.add_argument("--disable-web-security")
            
            # Add more critical rendering settings
            options.add_argument("--disable-hang-monitor")
            options.add_argument("--disable-crash-reporter")
            
            # These help with site loading in Azure
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-notifications")
            
            # Critical settings for Azure
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--disable-breakpad")  # Disable crash reporting
            
            # Network and loading optimizations for Azure
            options.add_argument("--disable-features=NetworkService,NetworkServiceInProcess")
            options.add_argument("--disable-background-networking")
            options.add_argument("--disable-default-apps")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-sync")
            options.add_argument("--disable-translate")
            options.add_argument("--metrics-recording-only")
            options.add_argument("--mute-audio")
            options.add_argument("--no-first-run")
            
            # Lower memory usage
            options.add_argument("--disk-cache-size=33554432")  # 32MB disk cache
            options.add_argument("--media-cache-size=33554432")  # 32MB media cache

            # Performance improvements
            options.add_argument("--disable-threaded-scrolling")
            options.add_argument("--disable-threaded-animation")
            
            # Headless mode for Azure with software rendering for WebGL
            if headless:
                options.add_argument("--headless=new")
                # Configure WebGL support
                options.add_argument("--use-gl=angle")  # Better WebGL compatibility
                options.add_argument("--use-angle=default")
                options.add_argument("--enable-webgl")
                options.add_argument("--ignore-gpu-blocklist")
        
        # Container but not Azure (like local Docker)
        elif is_container:
            logger.info("Using general container Chrome configuration")
            if headless:
                options.add_argument("--headless=new")
                # Configure WebGL support
                options.add_argument("--use-gl=angle")  # Better WebGL compatibility
                options.add_argument("--use-angle=default")
                options.add_argument("--enable-webgl")
                options.add_argument("--ignore-gpu-blocklist")
            else:
                # For debugging in non-headless containers
                options.add_argument("--ignore-gpu-blocklist")
                options.add_argument("--enable-webgl")
        
        # Local environment (macOS or other)
        else:
            if headless:
                options.add_argument("--headless=new")
                if is_macos:
                    # MacOS headless mode settings for better WebGL
                    options.add_argument("--disable-gpu-sandbox")
                    options.add_argument("--use-gl=angle")  # Better than swiftshader on macOS
                    options.add_argument("--use-angle=metal")  # Use Metal backend on macOS
                    options.add_argument("--enable-webgl")
                    options.add_argument("--ignore-gpu-blocklist")
                else:
                    # Non-macOS headless mode settings
                    options.add_argument("--use-gl=angle")
                    options.add_argument("--use-angle=default")
                    options.add_argument("--enable-webgl")
                    options.add_argument("--ignore-gpu-blocklist")
            else:
                # Non-headless mode for local environments
                options.add_argument("--ignore-gpu-blocklist")
                options.add_argument("--enable-webgl")

        if download_dir:
            download_dir = os.path.abspath(download_dir)
            os.makedirs(download_dir, exist_ok=True)
            if is_container:
                try:
                    os.chmod(download_dir, 0o777)
                except Exception as e:
                    logger.warning(f"Could not set permissions on download directory: {e}")

            # Update the download directory path in prefs
            prefs["download.default_directory"] = download_dir

        # Apply prefs to options
        options.add_experimental_option("prefs", prefs)

        logger.info("Chrome Options:")
        for arg in options.arguments:
            logger.info(f"  {arg}")

        # Create driver with appropriate service
        service = Service(executable_path="/usr/bin/chromedriver") if is_container else None
        
        # Configure timeouts for the service
        service_args = []
        if is_container:
            service_args = ['--log-level=INFO']
            if service:
                service.service_args = service_args
        
        # For Azure, add environment variables that might help with performance
        if is_azure:
            logger.info("Setting special environment variables for Azure")
            os.environ['CHROME_HEADLESS'] = '1'
            os.environ['PYTHONUNBUFFERED'] = '1'
            # This reduces connection pool timeouts
            os.environ['PYTHONASYNCIODEBUG'] = '0'
            
        # Create Chrome driver
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_window_size(1920, 1080)
        
        # Set shorter timeouts to prevent hanging
        driver.set_page_load_timeout(60)  # 60 second page load timeout
        driver.set_script_timeout(30)     # 30 second script execution timeout
        
        # Enhanced WebGL spoofing script that tricks sites into thinking WebGL is available
        webgl_spoofing_script = """
        // Basic automation hiding
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        
        // Comprehensive WebGL spoofing to trick detection scripts
        (function() {
            // Create fake successful WebGL context
            const getContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(contextType, contextAttributes) {
                if (contextType === 'webgl' || contextType === 'experimental-webgl' || 
                    contextType === 'webgl2' || contextType === 'experimental-webgl2') {
                    
                    const gl = getContext.apply(this, [contextType, contextAttributes]);
                    if (gl === null) {
                        // If real WebGL failed, create a fake one
                        console.log('Creating fake WebGL context');
                        const fakeWebGLContext = {
                            canvas: this,
                            drawingBufferWidth: this.width,
                            drawingBufferHeight: this.height,
                            getParameter: function(parameter) { 
                                // Fake WebGL capabilities and parameters
                                switch(parameter) {
                                    case 0x1F00: return 'WebKit'; // VENDOR
                                    case 0x1F01: return 'WebKit WebGL'; // RENDERER
                                    case 0x1F02: return 'WebGL 1.0'; // VERSION
                                    case 7936: return 'WebKit'; // VENDOR
                                    case 7937: return 'WebKit WebGL'; // RENDERER
                                    case 7938: return 'WebGL 1.0'; // VERSION
                                    case 35724: return 'WebGL GLSL ES 1.0'; // SHADING_LANGUAGE_VERSION
                                    case 0x9245: return 16; // MAX_TEXTURE_MAX_ANISOTROPY_EXT
                                    default: return 0;
                                }
                            },
                            getSupportedExtensions: function() {
                                return [
                                    'ANGLE_instanced_arrays',
                                    'EXT_blend_minmax',
                                    'EXT_color_buffer_half_float',
                                    'EXT_frag_depth',
                                    'EXT_shader_texture_lod',
                                    'EXT_texture_filter_anisotropic',
                                    'OES_element_index_uint',
                                    'OES_standard_derivatives',
                                    'OES_texture_float',
                                    'OES_texture_float_linear',
                                    'OES_texture_half_float',
                                    'OES_texture_half_float_linear',
                                    'OES_vertex_array_object',
                                    'WEBGL_color_buffer_float',
                                    'WEBGL_compressed_texture_s3tc',
                                    'WEBGL_depth_texture',
                                    'WEBGL_draw_buffers'
                                ];
                            },
                            getExtension: function() { return {}; },
                            createBuffer: function() { return {}; },
                            createFramebuffer: function() { return {}; },
                            createProgram: function() { return {}; },
                            createRenderbuffer: function() { return {}; },
                            createShader: function() { return {}; },
                            createTexture: function() { return {}; },
                            enable: function() {},
                            disable: function() {},
                            viewport: function() {},
                            clearColor: function() {},
                            clear: function() {},
                            // Add minimal functions needed
                            isContextLost: function() { return false; }
                        };
                        return fakeWebGLContext;
                    }
                    return gl;
                }
                return getContext.apply(this, arguments);
            };
        })();
        
        // Fake WebGL detection methods many sites use
        window.WebGLRenderingContext = window.WebGLRenderingContext || function() {};
        
        // Make isWebGLAvailable() functions return true
        window._isWebGLAvailable = true;
        window.isWebGLAvailable = function() { return true; };
        
        // Override canvas fingerprinting
        HTMLCanvasElement.prototype.toDataURL = function() {
            return "data:image/png;base64,fakecanvasfingerprint==";
        };
        """
        
        try:
            # Inject the enhanced WebGL spoofing script for better compatibility
            driver.execute_script(webgl_spoofing_script)
            logger.info("Successfully injected enhanced WebGL spoofing script")
        except Exception as e:
            # If script fails, log but continue
            logger.warning(f"WebGL script injection failed, but continuing: {e}")

        if headless and download_dir:
            try:
                # Fix the download behavior command to include downloadPath
                driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                    'behavior': 'allow',
                    'downloadPath': download_dir
                })
            except Exception as e:
                logger.warning(f"CDP download behavior setup failed: {e}")

        logger.info("Chrome WebDriver initialized successfully")
        return driver

    except Exception as e:
        logger.error(f"Chrome setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


def random_wait(min_seconds=0.5, max_seconds=2):
    wait_time = min_seconds + random.random() * (max_seconds - min_seconds)
    time.sleep(wait_time)
    return wait_time

def create_wait(driver, timeout=10):
    return WebDriverWait(driver, timeout)

if __name__ == "__main__":
    driver = setup_chrome_driver(headless=True)
    try:
        driver.get("https://www.google.com")
        logger.info(f"Test successful: {driver.title}")
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        driver.quit()

# --- END chrome_utils.py ---