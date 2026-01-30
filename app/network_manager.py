import subprocess
import time

class NetworkManager:
    def __init__(self, wifi_ssid, wifi_pass, hotspot_name="HoloScope_AP"):
        self.wifi_ssid = wifi_ssid
        self.wifi_pass = wifi_pass
        self.hotspot_name = hotspot_name

    def switch_to_hotspot(self):
        """Disconnects WiFi and starts the Access Point"""
        print(f"📡 Switching to Hotspot: {self.hotspot_name}...")
        try:
            # Down the wifi interface connection
            subprocess.run(["sudo", "nmcli", "con", "down", self.wifi_ssid], check=False)
            # Up the hotspot connection
            subprocess.run(["sudo", "nmcli", "con", "up", self.hotspot_name], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to start Hotspot: {e}")
            return False

    def switch_to_wifi(self):
        """Stops Hotspot and connects to Home WiFi"""
        print(f"🌐 Switching to WiFi: {self.wifi_ssid}...")
        try:
            # Down the hotspot
            subprocess.run(["sudo", "nmcli", "con", "down", self.hotspot_name], check=False)
            # Up the wifi
            subprocess.run(["sudo", "nmcli", "con", "up", self.wifi_ssid], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to connect to WiFi: {e}")
            return False

# Example usage for testing:
if __name__ == "__main__":
    net = NetworkManager(wifi_ssid="Your_Home_WiFi", wifi_pass="Your_Password")
    # net.switch_to_hotspot()