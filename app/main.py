import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from typing import List
from network_manager import NetworkManager

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

@app.get("/api/sensors")
async def read_sensors():
    # Mock data (On the Pi, we will replace this with real sensor code)
    return {"temp": 22.5, "humidity": 45}

@app.get("/api/files")
async def list_files():
    files = sorted(os.listdir(PHOTO_DIR), reverse=True)
    return [f for f in files if f.endswith(('.jpg', '.png', '.dng', '.csv'))]

@app.post("/api/settings")
async def save_settings(config: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(config, f)
    return {"status": "success"}

@app.post("/api/burst")
async def trigger_burst():
    settings = get_settings()
    # Mocking the shell command
    print(f"Executing: rpicam-still --burst -n --project {settings['project_name']}")
    return {"status": "success", "message": "Burst Started"}

@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    file_path = os.path.join(PHOTO_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/api/network/hotspot")
async def start_hotspot():
    success = nav.switch_to_hotspot()
    if success:
        return {"status": "Switching to Hotspot. Reconnect your Mac to HoloScope_AP"}
    return {"status": "Error"}

@app.post("/api/network/wifi")
async def start_wifi():
    success = nav.switch_to_wifi()
    if success:
        return {"status": "Switching to WiFi. Reconnect your Mac to your home network"}
    return {"status": "Error"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
