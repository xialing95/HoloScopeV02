import os
import json
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List
from network_manager import NetworkManager
from camera_manager import cam_manager 
from pydantic import BaseModel


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

# --- API ROUTES ---

import subprocess
from fastapi.responses import FileResponse
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

    if cam_manager.is_running:
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
    cam_manager._stop_event.clear()
    print("Preview Mode re-enabled")
    return {"status": "ready"}

''' 
==========================================
   Sensors Endpoint
========================================== 
'''
@app.get("/api/sensors")
async def read_sensors():
    # Mock data (On the Pi, we will replace this with real sensor code)
    return {"temp": 22.5, "humidity": 45}

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
        
        print(f"📸 Camera Updated: Shutter={settings.shutter}, ISO={settings.iso}")
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
    if cam_manager.is_running:
        return {"status": "error", "message": "A capture is already in progress."}
    
    background_tasks.add_task(
        cam_manager.run_burst_sequence, 
        req.project_name, req.burst_count, req.interval, req.burst_gap
    )
    return {"status": "success", "message": "Burst sequence started."}

@app.post("/api/capture/stop")
async def stop_burst():
    cam_manager.stop_capture()
    return {"status": "success", "message": "Stop signal sent."}

''' 
==========================================
   File Management Endpoints
========================================== 
'''

@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    file_path = os.path.join(PHOTO_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/api/files")
async def list_files():
    files = sorted(os.listdir(PHOTO_DIR), reverse=True)
    return [f for f in files if f.endswith(('.jpg', '.png', '.dng', '.csv'))]

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
    
    # We use a background task so the 200 OK response 
    # reaches your browser BEFORE the WiFi cuts out.
    if request.mode == "hotspot":
        background_tasks.add_task( NetworkManager.switch_to_hotspot)
        return {"status": "Success", "detail": "Switching to Hotspot..."}
    
    elif request.mode == "wifi":
        if not request.ssid or not request.password:
            return {"status": "Error", "detail": "SSID and Password required for WiFi mode"}
        
        background_tasks.add_task( NetworkManager.switch_to_wifi, request.ssid, request.password)
        return {"status": "Success", "detail": f"Connecting to {request.ssid}..."}
    
    return {"status": "Error", "detail": "Invalid mode"}


''' 
==========================================
   Main
========================================== 
'''
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
