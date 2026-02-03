import os
import shutil
import json
import time
import subprocess
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List
from network_manager import net_manager
from camera_manager import cam_manager 
from BME680_manager import sensors
from pydantic import BaseModel
from epdisplay_manager import display_manager

app = FastAPI()

# Path to your photo storage and settings
PHOTO_DIR = os.path.expanduser("~/HoloScopeV02/data")
SETTINGS_FILE = os.path.expanduser("~/HoloScopeV02/app/settings.json")

# Ensure the photo directory exists
os.makedirs(PHOTO_DIR, exist_ok=True)

# --- HELPER: Read/Write Settings ---
def get_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {"project_name": "HoloScope", "time_interval": 5}
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)
    
# Initial Boot Screen
display_manager.update_display(
    status="Cam: Ready | BME: Ready",
    mode="Idle",
    settings="Ready to access web portal"
)

'''
==========================================
   Preview Endpoint
========================================== 
'''
@app.get("/api/preview")
async def get_preview():
    # 1. Check if we should even be running
    if cam_manager._stop_event.is_set():
        return {"error": "Preview stopped"}

    if cam_manager.is_bursting:
        return {"error": "Camera busy with Timelapse"}
    
    preview_path = "/tmp/preview.jpg"
    
    # 2. Build command using your saved tuning (Shutter, ISO, AWB)
    # We use lower resolution for speed, but keep the exposure settings
    cmd = [
        "rpicam-still",
        "-o", preview_path,
        "--width", "1024", 
        "--height", "768",
        "--shutter", str(cam_manager.settings["shutter"]),
        "--gain", str(cam_manager.settings["iso"] / 100),
        "--nopreview",
        "--timeout", "1",
        "--immediate"
    ]

    # Add AWB or Manual Gains
    if cam_manager.settings["awb_enabled"]:
        cmd.extend(["--awb", "auto"])
    else:
        gains = f"{cam_manager.settings['red_gain']},{cam_manager.settings['blue_gain']}"
        cmd.extend(["--awbgains", gains])
    
    try:
        subprocess.run(cmd, check=True)
        return FileResponse(preview_path)
    except subprocess.CalledProcessError:
        return {"error": "Camera capture failed"}
    
    
    
@app.post("/api/preview/start")
async def start_preview_mode():
    # Check if a burst is currently active
    if cam_manager.is_bursting:
        raise HTTPException(
            status_code=409, 
            detail="Camera is busy: Burst sequence is currently running."
        )

    # If not bursting, proceed with preview setup
    cam_manager._stop_event.clear()
    cam_manager.is_previewing = True
    print("Preview Mode re-enabled")
    return {"status": "ready"}

''' 
==========================================
   Sensors Endpoint
========================================== 
'''
@app.get("/api/sensors")
async def read_sensors():
    data = sensors.get_readings()
    if not data:
        raise HTTPException(status_code=503, detail="BME680 sensor busy or not responding")
    return data

''' 
==========================================
   Health/Status Endpoints
========================================== 
'''
@app.get("/api/health")
async def get_health():
    """Returns status of camera, sensors, and disk"""
    import shutil
    
    # Camera info from manager
    cam_info = cam_manager.get_camera_info()
    cam_status = "OK" if cam_manager.is_previewing or cam_manager.is_bursting else "IDLE"
    
    # Disk usage
    disk = shutil.disk_usage("/")
    disk_total_gb = disk.total // (1024**3)
    disk_used_gb = disk.used // (1024**3)
    disk_pct = (disk.used / disk.total) * 100
    
    return {
        "camera_connected": cam_info["connected"],
        "camera_model": cam_info["model"],
        "camera_status": cam_status,
        "sensor": "OK",
        "disk": f"{disk_used_gb}/{disk_total_gb}GB"
    }

@app.get("/api/update_epdisplay")
async def update_epdisplay():
    import shutil
    
    # 1. Gather Camera & Mode Data
    cam_info = cam_manager.get_camera_info()
    is_busy = cam_manager.is_previewing or cam_manager.is_bursting
    
    # Define Line 2 (Status) and Line 3 (Mode)
    status_str = "CAM: OK" if cam_info["connected"] else "CAM: FAIL"
    
    if cam_manager.is_bursting:
        mode_str = "BURSTING"
    elif cam_manager.is_previewing:
        mode_str = "PREVIEW"
    else:
        mode_str = "IDLE"

    # 2. Gather Sensor Data (BME680)
    sensor_data = sensors.get_readings()
    if sensor_data:
        status_str += f" | {sensor_data['temp']}C"
    else:
        status_str += " | SEN: ERR"

    # 3. Gather Disk Data for Line 4 (Settings/Data)
    disk = shutil.disk_usage("/")
    disk_used_gb = disk.used // (1024**3)
    disk_total_gb = disk.total // (1024**3)
    storage_str = f"Disk: {disk_used_gb}/{disk_total_gb}GB"

    # 4. Check for Errors for Line 5
    err_msg = ""
    if not cam_info["connected"]:
        err_msg = "No Camera!"
    elif (disk.used / disk.total) > 0.90:
        err_msg = "Disk 90% Full"

    # Push to display
    display_manager.update_display(
        status=status_str,
        mode=mode_str,
        settings=storage_str,
        error=err_msg
    )
    
    return {"status": "Display Updated", "ip": display_manager.ip}

''' 
==========================================
   Camera Setting Management Endpoint
========================================== 
'''
class CameraSettings(BaseModel):
    shutter: int
    iso: int
    awb_enabled: bool
    red_gain: float
    blue_gain: float
    constrast: float
    brightness: float

@app.post("/api/settings")
async def save_settings(config: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(config, f)
    return {"status": "success"}

@app.post("/api/camera/settings")
async def update_camera_settings(settings: CameraSettings):
    try:
        # We pass the dictionary version of the model to our manager
        cam_manager.update_settings(settings.dict())
        
        print(f"Camera Updated: Shutter={settings.shutter}, ISO={settings.iso}")
        return {"status": "success", "message": "Camera settings updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

''' 
==========================================
   Burst Capture Endpoint
========================================== 
'''
class BurstRequest(BaseModel):
    project_name: str
    burst_count: int
    interval: int
    burst_gap: int

@app.post("/api/capture/burst")
async def start_burst(req: BurstRequest, background_tasks: BackgroundTasks):
    cam_manager.stop_capture()
    time.sleep(0.5)
    
    background_tasks.add_task(
        cam_manager.run_burst_sequence, 
        req.project_name, req.burst_count, req.interval, req.burst_gap
    )
    display_manager.update_display(
        settings="Burst sequence in progress..."
    )
    return {"status": "success", "message": "Burst sequence started."}

@app.post("/api/capture/stop")
async def stop_burst():
    cam_manager.stop_capture()
    cam_manager.is_previewing = False
    display_manager.update_display(
        settings="Burst sequence stopped."
    )
    return {"status": "success", "message": "Stop signal sent."}

''' 
==========================================
   File Management Endpoints
========================================== 
'''
@app.get("/api/files")
async def list_files():
    all_files = []
    # os.walk goes into every subfolder inside PHOTO_DIR
    for root, dirs, files in os.walk(PHOTO_DIR):
        for f in files:
            if f.endswith(('.jpg', '.png', '.dng', '.csv', '.txt')):
                # Get the path relative to PHOTO_DIR (e.g., "Project_123/image.dng")
                relative_path = os.path.relpath(os.path.join(root, f), PHOTO_DIR)
                all_files.append(relative_path)
    
    # Sort by newest first (using OS stats)
    all_files.sort(key=lambda x: os.path.getmtime(os.path.join(PHOTO_DIR, x)), reverse=True)
    return all_files

@app.get("/api/download/{file_path:path}")
async def download_file(file_path: str):
    # This joins /home/pi/HoloScopeV02/data + ProjectName/image.jpg
    full_path = os.path.join(PHOTO_DIR, file_path)
    
    if os.path.exists(full_path):
        return FileResponse(
            full_path, 
            media_type='application/octet-stream', 
            filename=os.path.basename(full_path)
        )
    
    # If it fails, let's see why in the logs
    print(f"File not found: {full_path}")
    return {"error": f"File not found at {full_path}"}

@app.delete("/api/files/{filename:path}") # Added :path to handle subfolder slashes
async def delete_file(filename: str):
    if filename == "delete-all":
        try:
            # Recreate the directory to wipe everything including folders
            shutil.rmtree(PHOTO_DIR)
            os.makedirs(PHOTO_DIR, exist_ok=True)
            return {"status": "success", "message": "All folders and files wiped"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # Handle individual file or folder deletion
    full_path = os.path.join(PHOTO_DIR, filename)
    if os.path.exists(full_path):
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="File not found")

''' 
==========================================
   Network Manager Endpoint
========================================== 
'''
# 1. Define the data structure expected from JS
class NetworkRequest(BaseModel):
    mode: str
    ssid: str = None  # Optional, only needed for wifi
    password: str = None

@app.post("/api/network")
async def handle_network(request: NetworkRequest, background_tasks: BackgroundTasks):
    """Unified endpoint to switch between Hotspot and WiFi"""
    
    if request.mode == "hotspot":
        # Update display immediately so you see the status while the Pi is working
        display_manager.update_display(
            status="Switching to AP...",
            mode="NETWORK",
            settings="Hotspot Mode"
        )
        
        background_tasks.add_task(net_manager.switch_to_hotspot)
        return {"status": "Success", "detail": "Switching to Hotspot. Check E-Ink for new IP."}
    
    elif request.mode == "wifi":
        if not request.ssid or not request.password:
            return {"status": "Error", "detail": "SSID and Password required for WiFi mode"}
        
        display_manager.update_display(
            status=f"Connecting...",
            mode="NETWORK",
            settings=f"SSID: {request.ssid}"
        )
        
        # FIX: Use the instance 'network_manager'
        background_tasks.add_task(
            net_manager.switch_to_wifi, 
            request.ssid, 
            request.password
        )
        return {"status": "Success", "detail": f"Connecting to {request.ssid}. Check E-Ink for status."}
    
    return {"status": "Error", "detail": "Invalid mode"}

''' 
==========================================
   Status Manager Endpoint
========================================== 
'''
@app.get("/api/status")
async def get_status():
    return {
        "is_previewing": cam_manager.is_previewing, # Boolean flag
        "is_bursting": cam_manager.is_bursting,       # Boolean flag
        "message": "Burst in Progress" if cam_manager.is_bursting else "System Ready"
    }

''' 
==========================================
   Main
========================================== 
'''
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
