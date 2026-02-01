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
            # Check if rpicam-still is available
            result = subprocess.run(
                ["which", "rpicam-still"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                self.camera_connected = False
                return

            # Try a quick capture to verify camera is working
            check_result = subprocess.run(
                ["rpicam-still", "--timeout", "100", "--nopreview", "-o", "/dev/null"],
                capture_output=True,
                text=True,
                timeout=15
            )

            # Check for camera-related errors in output
            stderr_lower = check_result.stderr.lower() if check_result.stderr else ""
            if check_result.returncode == 0:
                self.camera_connected = True
            elif "failed to detect" in stderr_lower or "no camera" in stderr_lower:
                self.camera_connected = False
            else:
                # Camera might be connected but something else failed
                self.camera_connected = True

            # Try to get sensor info using vcgencmd
            sensor_result = subprocess.run(
                ["vcgencmd", "get_camera"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if sensor_result.returncode == 0 and "detected=1" in sensor_result.stdout:
                output = sensor_result.stdout
                if "revision=1" in output or "imx477" in output.lower():
                    self.camera_model = "Raspberry Pi Camera HQ (IMX477)"
                elif "revision=2" in output or "imx708" in output.lower():
                    self.camera_model = "Raspberry Pi Camera v3 (IMX708)"
                elif "imx219" in output.lower():
                    self.camera_model = "Raspberry Pi Camera v2 (IMX219)"
                else:
                    self.camera_model = "Raspberry Pi Camera"
            else:
                self.camera_model = "Raspberry Pi Camera (Unknown)"

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

