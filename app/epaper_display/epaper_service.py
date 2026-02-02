#!/usr/bin/python
import sys
import os
import logging
import time
import socket
import subprocess
from datetime import datetime
from typing import Optional, Tuple

# --- Configuration & Setup ---

FONTDIC = "/home/pi/HoloScope/app/epaper_display/Font.ttc"
SECTION_HEIGHT = 40

# Try to import the EPD driver (Keep existing mock logic)
try:
    from . import epd2in13b_V4
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    # 1. Log the full traceback using the 'exception' level/method.
    #    The .exception() method is a shortcut for calling .error(..., exc_info=True).
    logging.exception(f"Failed to import EPD driver 'epd2in13b_V4'.: {e}")
try:
    EPD_DRIVER_LOADED = True
    # Define type hints for the imported classes
    EPD_Type = epd2in13b_V4.EPD
    Image_Type = Image.Image
    ImageDraw_Type = ImageDraw.ImageDraw
    ImageFont_Type = ImageFont.FreeTypeFont
except:
    logging.warning("import is wrong. Display functions will be skipped.")
    # Mock classes... (as in your original code)
    class MockEPD:
        def __init__(self): pass
        def init(self): pass
        def Clear(self): pass
        def display(self, *args): pass
        def sleep(self): pass
        def getbuffer(self, image): return bytearray()
        height = 250
        width = 122
    epd2in13b_V4 = type('MockEPDModule', (object,), {'EPD': MockEPD, 'epdconfig': type('MockConfig', (object,), {'module_exit': lambda cleanup: None})})
    EPD_DRIVER_LOADED = False
    EPD_Type = MockEPD
    Image_Type = type('MockImage', (object,), {})
    ImageDraw_Type = type('MockImageDraw', (object,), {})
    ImageFont_Type = type('MockImageFont', (object,), {})

logging.basicConfig(level=logging.INFO)

# --- Network Utilities (Keep as-is) ---
# ... (get_ip_address, get_hostname, get_wifi_name) ...

def get_ip_address():
    """Retrieves the local machine's primary IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Offline"

def get_hostname():
    """Retrieves the local machine's hostname."""
    try:
        return socket.gethostname()
    except Exception:
        return "Unknown Host"

def get_wifi_name():
    """Retrieves the current Wi-Fi SSID using 'iwgetid'."""
    try:
        result = subprocess.check_output(["iwgetid", "-r"]).decode().strip()
        return result if result else "Not Connected"
    except subprocess.CalledProcessError:
        return "NA"

# --- Drawing Functions for Each Section (Keep as-is - they are modular) ---

def draw_ip_hostname(draw: ImageDraw_Type, font: ImageFont_Type, ip: str, hostname: str, y_pos: int):
    """Draws the IP Address and Hostname in the first section (Y=0)."""
    text = f"Host: {hostname}"
    draw.text((5, y_pos), text, font=font, fill=0)
    text_ip = f"IP: {ip}"
    draw.text((5, y_pos + 15), text_ip, font=font, fill=0)

def draw_wifi_ssid(draw: ImageDraw_Type, font: ImageFont_Type, ssid: str, y_pos: int):
    """Draws the Wi-Fi SSID in the second section (Y=SECTION_HEIGHT * 1)."""
    text = f"SSID: {ssid}"
    draw.text((5, y_pos), text, font=font, fill=0)

def draw_dynamic_message(draw: ImageDraw_Type, font: ImageFont_Type, message: str, y_pos: int):
    """Draws a dynamic/updateable message (like time) in the fourth section (Y=SECTION_HEIGHT * 3)."""
    text = f"Time: {message}"
    draw.text((5, y_pos), text, font=font, fill=0)

# --- New Initialization Function for External Use ---

def initialize_epd_and_fonts() -> Optional[Tuple[EPD_Type, Image_Type, Image_Type, ImageFont_Type]]:
    """
    Initializes the EPD hardware, loads fonts, and creates image buffers.
    Returns: A tuple (epd, HBlackimage, HRYimage, font_section) or None on failure.
    """
    if not EPD_DRIVER_LOADED:
        logging.error("Cannot initialize: EPD driver or PIL missing.")
        return None

    try:
        epd = epd2in13b_V4.EPD()
        epd.init()
        epd.Clear()
        time.sleep(0.5)

        # Load Fonts
        try:
            font_section = ImageFont.truetype(FONTDIC, 16) 
        except IOError:
            logging.error(f"Font file not found at {FONTDIC}. Using default font.")
            font_section = ImageFont.load_default()
            
        # Create image buffers (250*122 for horizontal)
        HBlackimage = Image.new('1', (epd.height, epd.width), 255)
        HRYimage = Image.new('1', (epd.height, epd.width), 255)
        
        return epd, HBlackimage, HRYimage, font_section
        
    except Exception as e:
        logging.error(f"Failed to initialize EPD or Fonts: {e}")
        return None


# --- New Update Function for External Use ---

def update_epaper_display(
    epd: EPD_Type,
    HBlackimage: Image_Type,
    HRYimage: Image_Type,
    font_section: ImageFont_Type,
    ip: str,
    hostname: str,
    ssid: str,
    dynamic_message: str,
    y_section_pos: int = SECTION_HEIGHT
):
    """
    Clears the buffer, draws all sections with provided data, and updates the display.
    """
    # 1. Clear the drawing buffer
    HBlackimage.paste(255, [0, 0, epd.height, epd.width])
    drawblack = ImageDraw.Draw(HBlackimage)

    # 2. Call each drawing function with the external data
    draw_ip_hostname(drawblack, font_section, ip, hostname, 0)
    draw_wifi_ssid(drawblack, font_section, ssid, y_section_pos * 1)
    
    draw_dynamic_message(drawblack, font_section, dynamic_message, y_section_pos * 2)
    
    # 3. Send the complete image buffer to the display
    epd.display(epd.getbuffer(HBlackimage), epd.getbuffer(HRYimage))


# --- Main Execution Logic (Now acts as a demonstration/test loop) ---
def main(now_str: Optional[str] = None):
    """
    Main execution loop that orchestrates the data fetching and drawing.
    
    Args:
        now_str (Optional[str]): The message to display in the dynamic 
                                 section. If None, the current time is used.
    """
    # FIX: Determine the final value of now_str only ONCE at the start.
    if now_str is None:
        now_str = datetime.now().strftime("%H:%M:%S")

    init_result = initialize_epd_and_fonts()
    if init_result is None:
        return

    epd, HBlackimage, HRYimage, font_section = init_result

    # 1. Fetch Static Network Info (These won't change often)
    ip = get_ip_address()
    hostname = get_hostname()
    ssid = get_wifi_name()
    logging.info(f"Network Info | IP: {ip} | Host: {hostname} | SSID: {ssid}")

    # 2. Main Update Loop (Performs one full update)
    try:        
        # --- Drawing Orchestration using the new reusable function ---
        update_epaper_display(
            epd,
            HBlackimage,
            HRYimage,
            font_section,
            ip,
            hostname,
            ssid,
            now_str # Use the value determined at the top
        )

        # 3. Sleep
        logging.info("Goto Sleep...")
        epd.sleep()
        
    except Exception as e:
        # Log the full traceback for any unhandled exception in the try block
        logging.exception(f"An error occurred during the update loop: {e}")
        
    except KeyboardInterrupt:    
        logging.info("Ctrl + C detected: Exiting and cleaning up EPD module.")
        # Ensure cleanup on interrupt
        epd2in13b_V4.epdconfig.module_exit(cleanup=True)
        sys.exit()

if __name__ == "__main__":
    main()