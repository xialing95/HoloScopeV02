import subprocess
import time
import logging
from epdisplay_manager import display_manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NetworkManager")

class NetworkManager:
    def __init__(self, hotspot_name="HoloScopeAP"):
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
        # Update display BEFORE switching to show intent
        display_manager.update_display(status="Starting AP...", mode="NET-AP")
        
        success, output = self._run_cmd(["sudo", "nmcli", "con", "up", self.hotspot_name])
        
        # Give the Pi Zero a moment to assign the 192.168.4.1 IP
        time.sleep(5) 
        display_manager.update_display(status="Hotspot Active", mode="IDLE")
        return success

    def switch_to_wifi(self, ssid, password):
        """Attempts to connect to a WiFi network with a fallback to Hotspot"""
        logger.info(f"Attempting to connect to WiFi: {ssid}...")
        display_manager.update_display(status=f"Joining {ssid}...", mode="NET-WIFI")
        
        try:
            cmd = ["sudo", "nmcli", "dev", "wifi", "connect", ssid, "password", password]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("WiFi Connected successfully!")
                # Wait for DHCP to finish getting an IP
                time.sleep(5) 
                display_manager.update_display(status="WiFi Online", mode="IDLE")
                return True
            else:
                raise Exception("WiFi auth failed")

        except (subprocess.TimeoutExpired, Exception) as e:
            logger.warning(f"Connection failed. Falling back to Hotspot: {e}")
            display_manager.update_display(error="WiFi Fail: Fallback")
            self.switch_to_hotspot()
            return False

    def get_current_status(self):
        """Returns the current SSID or 'Hotspot'"""
        _, output = self._run_cmd(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"])
        for line in output.split('\n'):
            if line.startswith("yes:"):
                return line.split(":")[1]
        return "Unknown"

# --- SYSTEM SETUP ---
def setup_ap_profile(name="HoloScopeAP", password="fishystuff"):
    """Run once to create the AP profile in NetworkManager."""
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

# GLOBAL INSTANCE - Import this into main.py
net_manager = NetworkManager()