import subprocess
import time
import logging
from epdisplay_manager import display_manager
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NetworkManager")

class NetworkManager:
    def __init__(self, base_name="HoloScope"):
        self.interface = "wlan0"
        self.unique_id = self._get_serial_last_four()
        # The connection profile name in nmcli
        self.hotspot_name = "HoloscopeAP" 
        # The actual name people see on their phones
        self.ssid = f"{base_name}-{self.unique_id}"
    
    def _run_cmd(self, cmd):
        """Helper to run shell commands safely - Must be inside the class"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            # We use logger.error here (ensure logger is defined at top of file)
            print(f"Command failed: {' '.join(cmd)} - {e.stderr}")
            return False, e.stderr

    def _get_serial_last_four(self):
        """Fetches the last 4 characters of the Pi's serial number."""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('Serial'):
                        return line.strip()[-4:]
        except:
            return "XXXX" # Fallback if serial can't be read

    def ensure_hotspot_exists(self, password="holoscope_pass"):
        """Creates the profile using the unique SSID."""
        success, _ = self._run_cmd(["nmcli", "con", "show", self.hotspot_name])
        
        if not success:
            logger.info(f"Creating unique hotspot: {self.ssid}")
            create_cmd = [
                "sudo", "nmcli", "con", "add", "type", "wifi", 
                "ifname", self.interface, "con-name", self.hotspot_name, 
                "autoconnect", "no", "ssid", self.ssid, "mode", "ap", 
                "ipv4.method", "shared", "ipv4.addresses", "192.168.4.1/24",
                "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password
            ]
            self._run_cmd(create_cmd)
            # Ensure it uses the 2.4GHz band for compatibility
            self._run_cmd(["sudo", "nmcli", "con", "modify", self.hotspot_name, "802-11-wireless.band", "bg"])
        return True

    def switch_to_hotspot(self):
        """Activates the Access Point mode"""
        logger.info("Transitioning to Hotspot mode...")
        display_manager.update_display(status="Starting AP...", mode="NET-AP")
        
        # 1. Ensure profile exists
        self.ensure_hotspot_exists()

        # 2. Disconnect current wifi to free the radio
        self._run_cmd(["sudo", "nmcli", "device", "disconnect", self.interface])
        time.sleep(1)

        # 3. Bring the Hotspot up
        success, output = self._run_cmd(["sudo", "nmcli", "con", "up", self.hotspot_name])
        
        if success:
            time.sleep(5) # Wait for IP 192.168.4.1 to settle
            display_manager.update_display(status="Hotspot Active", mode="IDLE")
            logger.info("Hotspot is active at 192.168.4.1")
        else:
            display_manager.update_display(status="AP Error", mode="ERR")
            
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
def get_serial_last_four():
    """Helper to get unique hardware ID for the SSID."""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    return line.strip()[-4:]
    except Exception:
        return "XXXX"

def setup_ap_profile(name="HoloscopeAP", password="fishystuff"):
    """
    Creates a unique WiFi Hotspot profile.
    Internal Profile Name: 'HoloscopeAP'
    Broadcast SSID: 'HoloScope-XXXX'
    """
    unique_id = get_serial_last_four()
    ssid = f"HoloScope-{unique_id}"
    
    # 1. First, delete any existing profile with the name 'HoloscopeAP' to avoid conflicts
    subprocess.run(["sudo", "nmcli", "con", "delete", name], capture_output=True)

    # 2. Add the basic profile with the unique SSID
    # ipv4.method 'shared' is key: it tells NetworkManager to act as a router/DHCP server
    cmd = [
        "sudo", "nmcli", "con", "add", "type", "wifi", 
        "ifname", "wlan0", 
        "mode", "ap", 
        "con-name", name, 
        "ssid", ssid, 
        "autoconnect", "false",
        "ipv4.method", "shared",
        "ipv4.addresses", "192.168.4.1/24"
    ]
    subprocess.run(cmd)

    # 3. Apply security and band settings
    # We use 'bg' band (2.4GHz) because the Pi Zero handles it better than 5GHz/Auto
    subprocess.run(["sudo", "nmcli", "con", "modify", name, "802-11-wireless.band", "bg"])
    subprocess.run(["sudo", "nmcli", "con", "modify", name, "802-11-wireless-security.key-mgmt", "wpa-psk"])
    subprocess.run(["sudo", "nmcli", "con", "modify", name, "802-11-wireless-security.psk", password])

    print(f"Success: AP Profile '{name}' created with SSID: '{ssid}'")
    print(f"The dashboard will be available at http://192.168.4.1")

# GLOBAL INSTANCE - Import this into main.py
net_manager = NetworkManager()