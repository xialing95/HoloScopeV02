import subprocess
import os
import time
import threading
from datetime import datetime

class CameraManager:
    def __init__(self):
        self._stop_event = threading.Event()
        self.is_running = False

    def stop_capture(self):
        """Signals the loop to stop after the current photo/gap"""
        self._stop_event.set()

    def run_burst_sequence(self, project_name, burst_count, interval, burst_gap):
        self._stop_event.clear()
        self.is_running = True
        
        base_path = f"/home/pi/HoloScopeV02/photos/{project_name}"
        
        try:
            while not self._stop_event.is_set():
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                burst_path = f"{base_path}/burst_{timestamp}"
                os.makedirs(burst_path, exist_ok=True)

                # Construct the command
                # We use %03d so rpicam-still auto-numbers the burst files
                filename = f"{burst_path}/img_%03d.jpg"
                
                # Calculating total timeout based on your interval and count
                # Total time = (number of photos * interval in ms) + a small buffer
                total_timeout = (burst_count * interval * 1000) + 500

                cmd = [
                    "rpicam-still",
                    "--shutter", "500",
                    "--timeout", str(total_timeout),
                    "--timelapse", str(interval * 1000),
                    "--raw",
                    "--nopreview",
                    "-o", filename
                ]

                try:
                    # We run this as one process for the whole burst
                    subprocess.run(cmd, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Hardware Error: {e}")
                    break

                print(f"Burst {timestamp} complete. Sleeping for {burst_gap} minutes...")
                
                # Wait for the next burst gap
                for _ in range(burst_gap * 60):
                    if self._stop_event.is_set(): break
                    time.sleep(1)
        finally:
            self.is_running = False

# Global instance to be used by main.py
cam_manager = CameraManager()