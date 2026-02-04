/* ==========================================
   1. GLOBAL STATE & NOTIFICATIONS
   ========================================== */
const API_BASE = "/api";

/**
 * Updates the top status bar with messages and colors
 * @param {string} message - The text to display
 * @param {string} type - 'neutral', 'success', or 'error'
 */

function updateTrackingText(state) {
    const bar = document.getElementById('system-status-bar');
    const msg = document.getElementById('status-message');

    if (!bar || !msg) return;

    // Save the state globally so notify() can restore it after a timeout
    window.currentCameraState = state;

    // Mapping states to user-friendly text and CSS classes
    const stateMap = {
        'idle':      { text: "HoloScope Ready",      class: "status-ready" },
        'preview':   { text: "Live Preview Active",  class: "status-preview" },
        'recording': { text: "Recording Video...",   class: "status-recording" },
        'burst':     { text: "Burst Capture Active", class: "status-burst" },
        'busy':      { text: "Processing Data...",   class: "status-busy" },
        'logging':   { text: "Logging Sensors...",   class: "status-logging" }
    };

    // Get configuration based on state, default to idle if state is unknown
    const config = stateMap[state] || stateMap['idle'];

    // Update the UI
    msg.innerText = config.text;
    bar.className = ''; // Clear existing status classes
    bar.classList.add(config.class);

    console.log(`System State Change: ${state}`);
}

function notify(message, type = 'neutral') {
    const bar = document.getElementById('system-status-bar');
    const msg = document.getElementById('status-message');
    
    if (!bar || !msg) return;

    // 1. Update the visual state and main message
    msg.innerText = message;
    
    // We use a helper to ensure we keep the base status-bar styles
    bar.className = ''; 
    bar.classList.add(`status-${type}`);

    // 2. Logic for transient notifications (Success/Error)
    // We don't want "Settings Saved" to stay there forever.
    if (type === 'success' || type === 'error') {
        setTimeout(() => {
            // After 5 seconds, we don't just reset to "Ready"
            // We check if the poller is running to restore the correct state
            if (window.currentCameraState) {
                updateTrackingText(window.currentCameraState);
            } else {
                msg.innerText = "HoloScope Ready";
                bar.className = 'status-ready';
            }
        }, 5000);
    }
}

// --- UTILITY: Poll status of camera ---
async function pollStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const data = await response.json();
        
        // Save globally so notify() can see it
        window.currentCameraState = data;

        const tracker = document.getElementById('camera-tracker');

        if (data.is_previewing) {
            tracker.innerText = "[ PREVIEWING LIVE ]";
        } else if (data.is_bursting) {
            tracker.innerText = `[ BURST TIMELAPSE IN PROGRESS]`;
        } else {
            tracker.innerText = "[ CAMERA IDLE ]";
        }
    } catch (e) {
        tracker.innerText = "[ OFFLINE ]";
    }
}

// --- UTILITY: Safe Listener Attachment ---
const listen = (id, func) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('click', func);
};

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    
    // 1. Preview Controls
    listen('start-preview-btn', handleStartPreview);
    listen('stop-preview-btn', handleStopPreview);
    
    // 2. Burst Controls
    listen('burst-btn', handleBurstStart);
    listen('stop-btn', handleBurstStop); // Both stop buttons do the same
    
    // 3. Camera Tuning
    listen('save-settings-btn', applyCameraTuning);
    
    // 4. AWB Toggle Logic
    const awbToggle = document.getElementById('awb-toggle');
    if (awbToggle) {
        awbToggle.addEventListener('change', (e) => {
            document.getElementById('manual-wb-controls').style.display = e.target.checked ? 'none' : 'block';
        });
    }

    // 5. Files Management
    listen('refresh-btn', refreshFiles);
    listen('delete-all-btn', deleteAllFiles);

    // 6. Sensor Management
    listen('start-log-btn', startSensorLogging);
    listen('stop-log-btn', stopSensorLogging);

    // 7. Network
    listen('wifi-btn', () => handleNetworkUpdate('wifi'));
    listen('hotspot-btn', () => handleNetworkUpdate('hotspot'));
});

/* ==========================================
   2. ENVIRONMENTAL SENSORS
   ========================================== */
async function updateSensors() {
    try {
        const response = await fetch(`${API_BASE}/sensors`);
        if (!response.ok) throw new Error("Sensor data unavailable");
        
        const data = await response.json();
        document.getElementById('temp-val').innerText = `${data.temp}°C`;
        document.getElementById('hum-val').innerText = `${data.humidity}%`;
    } catch (err) {
        // We don't notify 'error' here to avoid spamming the UI if the 
        // sensor is just momentarily busy, but we log it.
        console.warn("Sensor poll failed:", err);
    }
}

// --- SENSOR START FUNCTION ---
async function startSensorLogging() {
    const logIntervalInput = document.getElementById('log-interval');
    const startBtn = document.getElementById('start-log-btn');
    const stopBtn = document.getElementById('stop-log-btn');
    const statusText = document.getElementById('log-status-text');

    const intervalValue = parseInt(logIntervalInput.value);
    
    // Validation
    if (isNaN(intervalValue) || intervalValue < 1) {
        alert("Please enter a valid interval (minimum 1 second).");
        return;
    }

    try {
        const response = await fetch('/api/sensors/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ interval: intervalValue, enabled: true })
        });

        if (response.ok) {
            statusText.innerText = "ACTIVE";
            statusText.style.color = "#28a745";
            startBtn.disabled = true;
            stopBtn.disabled = false;
            console.log("Logging started.");
        }
    } catch (error) {
        console.error('Start Log Error:', error);
    }
}

// --- SENSOR STOP FUNCTION ---
async function stopSensorLogging() {
    const startBtn = document.getElementById('start-log-btn');
    const stopBtn = document.getElementById('stop-log-btn');
    const statusText = document.getElementById('log-status-text');

    try {
        const response = await fetch('/api/sensors/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ interval: 60, enabled: false }) // Interval doesn't matter for stop
        });

        if (response.ok) {
            statusText.innerText = "STOPPED";
            statusText.style.color = "#dc3545";
            startBtn.disabled = false;
            stopBtn.disabled = true;
            console.log("Logging stopped.");
        }
    } catch (error) {
        console.error('Stop Log Error:', error);
    }
}

/* ==========================================
   3. FILE MANAGEMENT (GALLERY)
========================================== */

async function refreshFiles() {
    const fileList = document.getElementById('file-list');
    const refreshBtn = document.getElementById('refresh-btn');
    
    refreshBtn.disabled = true;
    refreshBtn.innerText = "Loading...";

    try {
        const response = await fetch(`${API_BASE}/files`);
        const files = await response.json(); // Array of strings like "Folder_Name/file.dng"

        fileList.innerHTML = '';

        if (files.length === 0) {
            fileList.innerHTML = '<p class="empty-msg">No images captured yet.</p>';
            return;
        }

        // 1. Group files by their parent folder
        const groups = {};
        files.forEach(path => {
            const parts = path.split('/');
            const folderName = parts.length > 1 ? parts[0] : "Root";
            if (!groups[folderName]) groups[folderName] = [];
            groups[folderName].push(path);
        });

        // 2. Render Groups
        for (const [folder, folderFiles] of Object.entries(groups)) {
            const groupSection = document.createElement('div');
            groupSection.className = 'folder-group';
            
            // Add a header for the folder with a "Delete Folder" option
            groupSection.innerHTML = `
                <div class="folder-header">
                    <strong>📁 ${folder}</strong>
                    ${folder !== "Root" ? `<button class="btn-text delete-btn" data-filename="${folder}">Delete Folder</button>` : ''}
                </div>
                <div class="folder-content"></div>
            `;

            const contentDiv = groupSection.querySelector('.folder-content');

            folderFiles.forEach(fullPath => {
                const shortName = fullPath.split('/').pop();
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                fileItem.innerHTML = `
                    <span class="file-name" title="${fullPath}">${shortName}</span>
                    <div class="file-actions">
                        <a href="${API_BASE}/download/${encodeURIComponent(fullPath)}" class="btn-small btn-green">↓</a>
                        <button class="btn-small btn-red delete-btn" data-filename="${fullPath}">×</button>
                    </div>
                `;
                contentDiv.appendChild(fileItem);
            });

            fileList.appendChild(groupSection);
        }

        // 3. Attach Listeners (Common for both folder and file buttons)
        fileList.querySelectorAll('.delete-btn').forEach(btn => {
            btn.onclick = (e) => {
                e.preventDefault();
                const fname = btn.getAttribute('data-filename');
                deleteFile(fname);
            };
        });

    } catch (err) {
        notify("Failed to load gallery", "error");
        console.error(err);
    } finally {
        refreshBtn.disabled = false;
        refreshBtn.innerText = "Refresh Gallery";
    }
}

async function deleteFile(filename) {
    // encodeURIComponent handles slashes in the filename for the URL
    const safeName = encodeURIComponent(filename);
    
    if (!confirm(`Permanently delete ${filename}?`)) return;
    
    try {
        const res = await fetch(`${API_BASE}/files/${safeName}`, { method: 'DELETE' });
        if (res.ok) {
            notify(`Deleted: ${filename}`, "success");
            refreshFiles();
        } else {
            const errorData = await res.json();
            throw new Error(errorData.detail || "Delete failed");
        }
    } catch (err) {
        notify(`Error: ${err.message}`, "error");
    }
}

// Note: This still calls the same endpoint, but uses "delete-all" keyword
async function deleteAllFiles() {
    if (!confirm("⚠️ DELETE EVERYTHING? This wipes all folders and files.")) return;

    try {
        const response = await fetch(`${API_BASE}/files/delete-all`, { method: 'DELETE' });
        if (response.ok) {
            notify("System wiped", "success");
            refreshFiles();
        }
    } catch (err) {
        notify("Failed to clear system", "error");
    }
}
/* ==========================================
   4. CAMERA SETTINGS & LOGGING
   ========================================== */
async function applyCameraTuning() {
    const payload = {
        shutter: parseInt(document.getElementById('shutter').value),
        iso: parseInt(document.getElementById('iso').value),
        awb_enabled: document.getElementById('awb-toggle').checked,
        red_gain: parseFloat(document.getElementById('red-gain').value),
        blue_gain: parseFloat(document.getElementById('blue-gain').value),
        contrast:parseFloat(document.getElementById('contrast').value),
        brightness:parseFloat(document.getElementById('brightness').value),
    };

    try {
        const response = await fetch(`${API_BASE}/camera/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (response.ok) notify("Camera Tuned!", "success");
    } catch (err) {
        notify("Tuning Failed", "error");
    }
}
/* ==========================================
   5. SYSTEM & NETWORK MANAGEMENT
   ========================================== */
// The function itself remains logic-heavy, but it no longer lives in the global scope
async function handleNetworkUpdate(mode) {
    const ssid = document.getElementById('wifi-ssid').value;
    const pass = document.getElementById('wifi-pass').value;

    // Hotspot doesn't necessarily need SSID/Pass inputs if they are hardcoded on the Pi,
    // but WiFi definitely does.
    if (mode === 'wifi' && (!ssid || !pass)) {
        notify("SSID and Password required for WiFi", "error");
        return;
    }

    const confirmMsg = mode === 'hotspot' 
        ? "Switching to Hotspot mode will disconnect the Pi from WiFi. Proceed?" 
        : `Connect to "${ssid}"? This may drop your current connection.`;

    if (!confirm(confirmMsg)) return;

    notify(`Switching to ${mode}...`, "neutral");

    try {
        const response = await fetch(`${API_BASE}/network`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                mode: mode, 
                ssid: ssid, 
                password: pass 
            })
        });

        if (response.ok) {
            notify("Network command sent! Reconnect in 30s.", "success");
        } else {
            const errorData = await response.json();
            notify(`Network Error: ${errorData.detail || "Failed"}`, "error");
        }
    } catch (err) {
        // This is expected! The Pi's radio resets, killing the fetch request.
        notify("Network switching... Please wait and check your Wi-Fi list.", "success");
    }
}

/* ==========================================
   6. BURST INITIALIZATION & LOOPS
   ========================================== */
async function handleBurstStart() {
    // 1. Stop the local JS preview timer so it stops hammering /api/preview
    if (previewInterval) {
        clearInterval(previewInterval);
        previewInterval = null;
    }

    const payload = {
        project_name: document.getElementById('proj-name').value,
        burst_count: parseInt(document.getElementById('burst-count').value),
        interval: parseInt(document.getElementById('time-interval').value),
        burst_gap: parseInt(document.getElementById('burst-gap').value),
        total_duration: parseFloat(document.getElementById('total-duration').value)
    };

    // Validations
    if (!payload.project_name) return notify("Name required!", "error");
    if (payload.interval < 2) return notify("Min interval is 2s", "error");
    if (!payload.burst_count) return notify("Number of photos required!", "error");
    if (!payload.total_duration || payload.total_duration < 0.015) {
        return notify("Duration must be at least 1 min", "error");
    }

    notify(`Project ${payload.project_name} started...`, "success");

    try {
        const response = await fetch(`${API_BASE}/capture/burst`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            notify("Burst Active - Preview Paused", "success");
        } else {
            notify("Failed to start burst", "error");
        }
    } catch (err) {
        console.error(err);
        notify("Connection error", "error");
    }
};

async function handleBurstStop() {
    // Disable the button immediately to prevent double-clicks
    const stopBtn = document.getElementById('stop-btn');
    stopBtn.disabled = true;
    stopBtn.innerText = "Stopping...";

    try {
        const response = await fetch(`${API_BASE}/capture/stop`, {
            method: 'POST'
        });

        if (response.ok) {
            notify("Stop signal sent! Finishing current photo...", "neutral");
        } else {
            notify("Failed to stop capture", "error");
        }
    } catch (err) {
        notify("Connection error", "error");
    } finally {
        // Re-enable after a short delay
        setTimeout(() => {
            stopBtn.disabled = false;
            stopBtn.innerText = "Stop Capture";
        }, 2000);
    }
};

/* ==========================================
   7. PREVIEW MANAGEMENT
   ========================================== */
let previewInterval = null;

async function handleStartPreview() {
    // 1. Tell the Pi to reset the stop flag
    const response = await fetch(`${API_BASE}/preview/start`, { method: 'POST' });
    
    if (response.ok) {
        if (previewInterval) clearInterval(previewInterval);
        
        notify("Preview Started", "success");

        previewInterval = setInterval(async () => {
            const img = document.getElementById('live-preview');

            if (img) {
                // Adding the timestamp 't' prevents the browser from caching a 'failed' image
                img.src = `${API_BASE}/preview?t=${new Date().getTime()}`;
            } else {
                console.error("Critical: 'live-preview' element not found.");
                clearInterval(previewInterval);
            }
        }, 3000);
    }
}

async function handleStopPreview() {
    // 1. Tell the Server to stop
    await fetch(`${API_BASE}/capture/stop`, { method: 'POST' });
    
    // 2. Clear the local JS interval
    if (previewInterval) {
        clearInterval(previewInterval);
        previewInterval = null;
    }
    
    notify("Preview Stopped", "neutral");
}

/* ==========================================
   8. UPDATE STATUS MANAGEMENT
   ========================================== */
async function updateHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        const camEl = document.getElementById('health-cam');
        const sensorEl = document.getElementById('health-sensor');
        const diskEl = document.getElementById('health-disk');
        
        // Compact format for health pills
        const camStatus = data.camera_connected 
            ? `${data.camera_model}` 
            : "No Cam";
        if (camEl) camEl.innerText = `CAM:${camStatus}`;
        
        if (sensorEl) sensorEl.innerText = `SENS:${data.sensor}`;
        if (diskEl) {
            // Compact disk format: "6/28GB" instead of "6/28GB (21.4%)"
            const diskMatch = data.disk.match(/(\d+\/\d+GB)/);
            diskEl.innerText = diskMatch ? `DSK:${diskMatch[1]}` : `DSK:${data.disk}`;
        }
    } catch (err) {
        console.warn("Health poll failed:", err);
    }
}

// Function to trigger the E-Ink refresh and update the web UI health
async function refreshEpdisplay() {
    console.log("Refreshing system health and E-Ink display...");
    
    try {
        // 1. Trigger the E-Ink hardware update
        const displayResponse = await fetch('/api/update_epdisplay');
        
        console.log("System update complete. Next update in 2 minutes.");
    } catch (error) {
        console.error("Failed to refresh system status:", error);
    }
}


// Start Polling
setInterval(updateSensors, 2000);  
setInterval(pollStatus, 2000); 
setInterval(updateHealth, 5000);  // Update health every 5 seconds
// setInterval(refreshEpdisplay, 120000); // Refresh every 2 minutes
// Run once on page load
refreshFiles();
updateHealth();
refreshEpdisplay();

