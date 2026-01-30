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
        self._stop_event.set()

    def run_burst_sequence(self, project_name, burst_count, interval, burst_gap):
        self._stop_event.clear()
        self.is_running = True
        
        # Save everything directly to the project folder
        base_path = f"/home/pi/HoloScopeV02/data/{project_name}"
        os.makedirs(base_path, exist_ok=True)
        
        try:
            while not self._stop_event.is_set():
                for i in range(burst_count):
                    if self._stop_event.is_set():
                        break
                    
                    # LONG UNIQUE FILENAME: project_date_time_index.jpg
                    # This ensures files are unique and sortable by name
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{base_path}/{project_name}_{timestamp}_{i:03d}.dnf"

                    cmd = [
                        "rpicam-still",
                        "--shutter", "500",
                        "--timeout", "1",
                        "--immediate",
                        "--raw",
                        "--nopreview",
                        "-o", filename
                    ]

                    subprocess.run(cmd, check=True)
                    
                    if i < burst_count - 1:
                        time.sleep(interval)

                if self._stop_event.is_set():
                    break

                # Responsive sleep for the burst gap
                for _ in range(int(burst_gap * 60)):
                    if self._stop_event.is_set(): break
                    time.sleep(1)
        finally:
            self.is_running = False

cam_manager = CameraManager()