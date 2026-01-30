import os
import json
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
   Setting Management Endpoint
========================================== 
'''
@app.post("/api/settings")
async def save_settings(config: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(config, f)
    return {"status": "success"}

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

@app.post("/api/burst")
async def trigger_burst():
    settings = get_settings()
    # Mocking the shell command
    print(f"Executing: rpicam-still --burst -n --project {settings['project_name']}")
    return {"status": "success", "message": "Burst Started"}

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
