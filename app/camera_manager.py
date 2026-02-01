import subprocess
import os
import time
import threading
from datetime import datetime

class CameraManager:
    def __init__(self):
        self.is_previewing = False
        self.is_bursting = False
        self.camera_model = None
        self.camera_connected = False

        self._stop_event = threading.Event()
        # Default settings that get overwritten by the Web UI
        self.settings = {
            "shutter": 500,
            "iso": 100,
            "awb_enabled": True,
            "red_gain": 1.5,
            "blue_gain": 1.5,
            "contrast": 1.0,
            "brightness": 0.0
        }

        # Detect camera on init
        self._detect_camera()

    def _detect_camera(self):
        """Detect if camera is connected and get model info using rpicam"""
        try:
            # Use rpicam-hello --list-cameras to detect camera
            list_result = subprocess.run(
                ["rpicam-hello", "--list-cameras"],
                capture_output=True,
                text=True,
                timeout=10
            )

            output = list_result.stdout.lower()
            stderr = list_result.stderr.lower() if list_result.stderr else ""

            # Check if camera was detected
            if list_result.returncode == 0 and "detected" in output:
                self.camera_connected = True

                # Parse camera model from output
                if "imx477" in output:
                    self.camera_model = "IMX477"
                elif "imx708" in output:
                    self.camera_model = "IMX708"
                elif "imx219" in output:
                    self.camera_model = "IMX219"
                elif "imx296" in output:
                    self.camera_model = "IMX296"
                elif "imx462" in output:
                    self.camera_model = "IMX462"
                else:
                    self.camera_model = "Raspberry Pi Camera"
            else:
                self.camera_connected = False
                self.camera_model = "No Camera Detected"

        except Exception as e:
            print(f"Camera detection failed: {e}")
            self.camera_connected = False

    def get_camera_info(self):
        """Return camera connection status and model"""
        return {
            "connected": self.camera_connected,
            "model": self.camera_model or "Unknown"
        }

    def update_settings(self, new_settings: dict):
        """Update the internal settings dictionary with new values from the UI."""
        self.settings.update(new_settings)

    def stop_capture(self):
        self._stop_event.set()
        # Force kill any hanging camera processes to free the hardware
        os.system("pkill -9 rpicam-still")

    def run_burst_sequence(self, project_name, burst_count, interval, burst_gap):
        self._stop_event.clear()
        self.is_bursting = True

        base_path = f"/home/pi/HoloScopeV02/data/"
        os.makedirs(base_path, exist_ok=True)

        try:
            while not self._stop_event.is_set():
                for i in range(burst_count):
                    if self._stop_event.is_set():
                        break

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{base_path}/{project_name}_{timestamp}_{i:03d}.dng"

                    # DYNAMIC COMMAND BUILDING
                    cmd = [
                        "rpicam-still",
                        "--shutter", str(self.settings["shutter"]),
                        "--gain", str(self.settings["iso"] / 100), # Convert ISO to analog gain
                        "--timeout", "1",
                        "--immediate",
                        "--raw",
                        "--nopreview",
                        "-o", filename
                    ]

                    # Inject AWB or Manual Gains
                    if self.settings["awb_enabled"]:
                        cmd.extend(["--awb", "auto"])
                    else:
                        gains = f"{self.settings['red_gain']},{self.settings['blue_gain']}"
                        cmd.extend(["--awbgains", gains])

                    subprocess.run(cmd, check=True)

                    if i < burst_count - 1:
                        time.sleep(interval)

                if self._stop_event.is_set():
                    break

                # Responsive sleep for the burst gap
                for _ in range(int(burst_gap * 60)):
                    if self._stop_event.is_set(): break
                    time.sleep(1)
                self.is_bursting = True
        finally:
            self.is_bursting = False
            self.current_frame = 0

cam_manager = CameraManager()

