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

            # Debug output - remove in production
            print(f"rpicam-hello stdout: {list_result.stdout[:300]}")
            print(f"rpicam-hello stderr: {list_result.stderr[:300] if list_result.stderr else 'none'}")

            # Check if camera was detected - look for various indicators
            has_camera = False
            combined_output = output + " " + stderr

            # Look for camera indicators in output
            if "available cameras" in combined_output or "0 :" in combined_output:
                has_camera = True
            elif "imx477" in combined_output or "imx708" in combined_output or "imx219" in combined_output:
                has_camera = True
            elif "connected" in combined_output:
                has_camera = True

            if has_camera:
                self.camera_connected = True

                # Parse camera model from output
                if "imx477" in combined_output:
                    self.camera_model = "IMX477"
                elif "imx708" in combined_output:
                    self.camera_model = "IMX708"
                elif "imx219" in combined_output:
                    self.camera_model = "IMX219"
                elif "imx296" in combined_output:
                    self.camera_model = "IMX296"
                elif "imx462" in combined_output:
                    self.camera_model = "IMX462"
                else:
                    self.camera_model = "Pi Camera"
            else:
                self.camera_connected = False
                self.camera_model = "No Camera"

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

        # Base data directory
        base_data_path = "/home/pi/HoloScopeV02/data"
        
        try:
            while not self._stop_event.is_set():
                # 1. Create a unique folder for THIS specific burst
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                session_dir = os.path.join(base_data_path, f"{project_name}_{timestamp}")
                os.makedirs(session_dir, exist_ok=True)

                # 2. Generate the Log Sheet (Manifest)
                log_path = os.path.join(session_dir, "metadata_log.txt")
                with open(log_path, "w") as log:
                    log.write(f"--- HOLOSCOPE SESSION LOG ---\n")
                    log.write(f"Project: {project_name}\n")
                    log.write(f"Timestamp: {timestamp}\n")
                    log.write(f"Camera Model: {self.camera_model}\n")
                    log.write(f"Settings: {self.settings}\n")
                    log.write(f"Burst Count: {burst_count}\n")
                    log.write(f"Interval: {interval}s\n")
                    log.write(f"Burst Gap: {burst_gap}m\n")
                    log.write(f"----------------------------\n")

                # 3. Build the rpicam-still command using --timelapse
                # This keeps the camera process alive for the whole burst
                filename_pattern = os.path.join(session_dir, f"{timestamp}_int{interval}_%04d.dng")
                
                cmd = [
                    "rpicam-still",
                    "--shutter", str(self.settings["shutter"]),
                    "--gain", str(self.settings["iso"] / 100),
                    "--timelapse", str(int(interval * 1000)), # Convert seconds to ms
                    "--timeout", str(burst_count*int(interval * 1000)+500), # Total duration + buffer
                    "--raw",                                  # Capture DNG
                    "--nopreview",
                    "-o", filename_pattern
                ]

                if self.settings["awb_enabled"]:
                    cmd.extend(["--awb", "auto"])
                else:
                    gains = f"{self.settings['red_gain']},{self.settings['blue_gain']}"
                    cmd.extend(["--awbgains", gains])

                # 4. Run the burst as a single process
                print(f"Starting burst of {burst_count} images in {session_dir}")
                subprocess.run(cmd, check=True)

                # 5. Handle the Burst Gap (convert minutes to seconds)
                if not self._stop_event.is_set():
                    print(f"Burst complete. Waiting {burst_gap} minutes for next gap...")
                    for _ in range(int(burst_gap * 60)):
                        if self._stop_event.is_set(): break
                        time.sleep(1)
                
        except Exception as e:
            print(f"Burst error: {e}")
        finally:
            self.is_bursting = False

cam_manager = CameraManager()

