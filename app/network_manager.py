import subprocess
import time
import logging
from epdisplay_manager import display_manager

# Setup logging to see what's happening in the background
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NetworkManager")

class NetworkManager:
    def __init__(self, hotspot_name="HoloScope_AP"):
        self.hotspot_name = hotspot_name
        self.interface = "wlan0"

    def _run_cmd(self, cmd):
        """Helper to run shell commands safely"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(cmd)} - {e.stderr}")
            return False, e.stderr

    def switch_to_hotspot(self):
        """Activates the Access Point mode"""
        logger.info("Transitioning to Hotspot mode...")
        # nmcli con up will automatically handle disconnecting from existing WiFi
        success, output = self._run_cmd(["sudo", "nmcli", "con", "up", self.hotspot_name])
        display_manager.update_display()
        return success

    def switch_to_wifi(self, ssid, password):
        """Attempts to connect to a WiFi network with a fallback to Hotspot"""
        logger.info(f"Attempting to connect to WiFi: {ssid}...")
        
        # 1. Try to connect to the new WiFi
        # We use a 30 second timeout for the connection attempt
        try:
            cmd = [
                "sudo", "nmcli", "dev", "wifi", "connect", 
                ssid, "password", password
            ]
            # Running with a timeout so we don't hang forever
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("WiFi Connected successfully!")
                display_manager.update_display()
                return True
            else:
                raise Exception("WiFi auth failed")

        except (subprocess.TimeoutExpired, Exception) as e:
            logger.warning(f"Connection failed. Falling back to Hotspot: {e}")
            self.switch_to_hotspot()
            return False

    def get_current_status(self):
        """Returns the current SSID or 'Hotspot'"""
        _, output = self._run_cmd(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"])
        for line in output.split('\n'):
            if line.startswith("yes:"):
                return line.split(":")[1]
        return "Unknown"

# --- REQUIRED ONE-TIME SYSTEM SETUP ---
# Run this function once or run the commands in your terminal to create the AP profile
def setup_ap_profile(name="HoloScope_AP", password="fishystuff"):
    """
    Creates the persistent Hotspot profile in NetworkManager if it doesn't exist.
    """
    cmd = [
        "sudo", "nmcli", "con", "add", "type", "wifi", "ifname", "wlan0", 
        "mode", "ap", "con-name", name, "ssid", name, "autoconnect", "false"
    ]
    subprocess.run(cmd)
    subprocess.run(["sudo", "nmcli", "con", "modify", name, "802-11-wireless.band", "bg"])
    subprocess.run(["sudo", "nmcli", "con", "modify", name, "802-11-wireless-security.key-mgmt", "wpa-psk"])
    subprocess.run(["sudo", "nmcli", "con", "modify", name, "802-11-wireless-security.psk", password])
    subprocess.run(["sudo", "nmcli", "con", "modify", name, "ipv4.method", "shared"])
    print(f"AP Profile '{name}' created.")