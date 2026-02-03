import os
import socket
import threading
import time
from PIL import Image, ImageDraw, ImageFont

try:
    from epaper_display import epd2in13b_V4
except ImportError:
    epd2in13b_V4 = None

class EPDisplayManager:
    def __init__(self):
        self.hostname = socket.gethostname()
        self.lock = threading.Lock() 
        
        # Initial data fetch
        self.ip = self.get_ip_fast()
        self.ssid = self.get_ssid_fast()
        
        self.lines = {
            "network": f"{self.ssid} | {self.ip}", # Line 1 now includes SSID
            "status": "Initializing...",
            "mode": "BOOT",
            "settings": "-",
            "error": ""
        }
        
        if epd2in13b_V4:
            self.epd = epd2in13b_V4.EPD()
        
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        font_bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        
        if os.path.exists(font_path):
            self.font_small = ImageFont.truetype(font_path, 11) # Slightly smaller for more info
            self.font_bold = ImageFont.truetype(font_bold_path, 14)
        else:
            self.font_small = self.font_bold = ImageFont.load_default()

    def get_ip_fast(self):
        try:
            ips = os.popen('hostname -I').read().strip()
            return ips.split()[0] if ips else "No IP"
        except:
            return "127.0.0.1"

    def get_ssid_fast(self):
        """Quickly fetch the current SSID."""
        try:
            # -r returns just the SSID name
            ssid = os.popen('iwgetid -r').read().strip()
            return ssid if ssid else "No WiFi"
        except:
            return "Unknown"

    def update_display(self, status=None, mode=None, settings=None, error=""):
        with self.lock:
            # Refresh Network Stats
            self.ip = self.get_ip_fast()
            self.ssid = self.get_ssid_fast()
            
            # Formatting Line 1: SSID | IP (Host is removed to save space)
            self.lines["network"] = f"{self.ssid} | {self.ip}"
            
            if status: self.lines["status"] = status
            if mode: self.lines["mode"] = mode.upper()
            if settings: self.lines["settings"] = settings
            self.lines["error"] = error
            
            self._draw()

    def _draw(self):
        if not epd2in13b_V4:
            print(f"DISPLAY MOCK: {self.lines}")
            return

        try:
            self.epd.init()
            img_b = Image.new('1', (self.epd.height, self.epd.width), 255)
            img_r = Image.new('1', (self.epd.height, self.epd.width), 255)
            
            draw_b = ImageDraw.Draw(img_b)
            draw_r = ImageDraw.Draw(img_r)

            # --- Layout ---
            # Line 1: Header (SSID and IP)
            draw_b.rectangle((0, 0, 250, 18), fill=0)
            draw_b.text((5, 2), self.lines["network"], font=self.font_small, fill=1)

            # Line 2: Status
            draw_b.text((5, 22), f"SYS: {self.lines['status']}", font=self.font_small, fill=0)

            # Line 3: Mode
            draw_b.text((5, 42), f"MODE: {self.lines['mode']}", font=self.font_bold, fill=0)

            # Line 4: Settings/Message
            draw_b.text((5, 64), f"MSG: {self.lines['settings']}", font=self.font_small, fill=0)

            # Line 5: Error (RED Buffer)
            if self.lines["error"]:
                draw_r.text((5, 88), f"ERR: {self.lines['error']}", font=self.font_small, fill=0)
                draw_r.rectangle((2, 85, 248, 118), outline=0)

            self.epd.display(self.epd.getbuffer(img_b), self.epd.getbuffer(img_r))
            self.epd.sleep()
        except Exception as e:
            print(f"Display Error: {e}")

# Global instance
display_manager = EPDisplayManager()