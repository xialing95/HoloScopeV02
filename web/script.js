/* ==========================================
   1. GLOBAL STATE & NOTIFICATIONS
   ========================================== */
const API_BASE = "/api";

/**
 * Updates the top status bar with messages and colors
 * @param {string} message - The text to display
 * @param {string} type - 'neutral', 'success', or 'error'
 */
function notify(message, type = 'neutral') {
    const bar = document.getElementById('system-status-bar');
    const msg = document.getElementById('status-message');
    
    if (!bar || !msg) return; // Guard clause if HTML isn't ready

    msg.innerText = message;
    bar.className = `status-${type}`;

    // Reset to neutral after 5 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            msg.innerText = "HoloScope Ready";
            bar.className = 'status-neutral';
        }, 5000);
    }
}

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

/* ==========================================
   3. FILE MANAGEMENT (GALLERY)
   ========================================== */
const refreshBtn = document.getElementById('refresh-btn');
const fileList = document.getElementById('file-list');

async function updateGallery() {
    refreshBtn.disabled = true;
    refreshBtn.innerText = "Loading...";

    try {
        const response = await fetch(`${API_BASE}/files`);
        const files = await response.json();

        // Clear current list
        fileList.innerHTML = '';

        if (files.length === 0) {
            fileList.innerHTML = '<p class="empty-msg">No images captured yet.</p>';
        } else {
            files.forEach(fileName => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';
                
                // Extract just the name if it's a long path
                const shortName = fileName.split('/').pop();
                
                fileItem.innerHTML = `
                    <span class="file-name" title="${fileName}">${shortName}</span>
                    <div class="file-actions">
                        <a href="${API_BASE}/download/${fileName}" class="btn-small">Download</a>
                    </div>
                `;
                fileList.appendChild(fileItem);
            });
        }
    } catch (err) {
        notify("Failed to load gallery", "error");
        console.error(err);
    } finally {
        refreshBtn.disabled = false;
        refreshBtn.innerText = "🔄 Refresh Gallery";
    }
}

// Attach event listener
refreshBtn.addEventListener('click', updateGallery);

// Run once on page load
updateGallery();

async function refreshFiles() {
    try {
        const res = await fetch(`${API_BASE}/files`);
        if (!res.ok) throw new Error("Could not fetch file list");
        
        const files = await res.json();
        const container = document.getElementById('file-list');
        
        if (files.length === 0) {
            container.innerHTML = '<p class="empty-msg">No files found.</p>';
            return;
        }

        container.innerHTML = ''; 
        files.forEach(file => {
            const row = document.createElement('div');
            row.className = 'file-item'; // Matches your responsive CSS
            row.style = "display:flex; justify-content:space-between; padding:8px; border-bottom:1px solid #333;";
            row.innerHTML = `
                <span>${file}</span>
                <div class="file-actions">
                    <a href="${API_BASE}/download/${file}" class="btn-blue" style="padding:5px 10px; text-decoration:none; margin-right:5px;">↓</a>
                    <button class="btn-warn" onclick="deleteFile('${file}')" style="width:auto; padding:5px 10px;">x</button>
                </div>
            `;
            container.appendChild(row);
        });
    } catch (err) {
        notify(`Gallery Error: ${err.message}`, "error");
    }
}

async function deleteFile(filename) {
    if (!confirm(`Permanently delete ${filename}?`)) return;
    
    try {
        const res = await fetch(`${API_BASE}/files/${filename}`, { method: 'DELETE' });
        if (res.ok) {
            notify(`Deleted ${filename}`, "success");
            refreshFiles();
        } else {
            throw new Error("Delete failed on server");
        }
    } catch (err) {
        notify(`Error: ${err.message}`, "error");
    }
}

/* ==========================================
   4. CAMERA SETTINGS & LOGGING
   ========================================== */
document.getElementById('save-settings-btn').addEventListener('click', applyCameraTuning);

async function applyCameraTuning() {
    const payload = {
        shutter: parseInt(document.getElementById('shutter').value),
        iso: parseInt(document.getElementById('iso').value),
        awb_enabled: document.getElementById('awb-toggle').checked,
        red_gain: parseFloat(document.getElementById('red-gain').value),
        blue_gain: parseFloat(document.getElementById('blue-gain').value)
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
async function updateNetwork(mode) {
    const ssid = document.getElementById('wifi-ssid').value;
    const pass = document.getElementById('wifi-pass').value;

    if (!ssid || !pass) {
        notify("SSID and Password required", "error");
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
            body: JSON.stringify({ mode, ssid, password: pass })
        });

        if (response.ok) {
            notify("Network command sent! Reconnect in 30s.", "success");
        } else {
            const errorData = await response.json();
            notify(`Network Error: ${errorData.detail || "Failed"}`, "error");
        }
    } catch (err) {
        // This catch block often triggers because the Pi's Wi-Fi restarts, 
        // breaking the connection before the response finishes.
        notify("Network switching... Check your Wi-Fi settings.", "success");
    }
}

/* ==========================================
   6. BURST INITIALIZATION & LOOPS
   ========================================== */
document.getElementById('burst-btn').addEventListener('click', async () => {
    const payload = {
        project_name: document.getElementById('proj-name').value,
        burst_count: parseInt(document.getElementById('burst-count').value),
        interval: parseInt(document.getElementById('time-interval').value),
        burst_gap: parseInt(document.getElementById('burst-gap').value)
    };

    if (!payload.project_name) return notify("Name required!", "error");
    if (payload.interval < 2) return notify("Min interval is 2s", "error");

    notify(`Project ${payload.project_name} started...`, "success");

    await fetch(`${API_BASE}/capture/burst`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
});

document.getElementById('stop-btn').addEventListener('click', async () => {
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
});

/* ==========================================
   7. PREVIEW MANAGEMENT
   ========================================== */
let previewInterval = null;

async function startPreview() {
    // 1. Tell the Pi to reset the stop flag
    const response = await fetch(`${API_BASE}/preview/start`, { method: 'POST' });
    
    if (response.ok) {
        if (previewInterval) clearInterval(previewInterval);
        
        notify("Preview Started", "success");

        previewInterval = setInterval(async () => {
            const img = document.getElementById('preview-frame');
            // Adding the timestamp 't' prevents the browser from caching a 'failed' image
            img.src = `${API_BASE}/api/preview?t=${new Date().getTime()}`;
        }, 3000); 
    }
}

async function stopPreview() {
    // 1. Tell the Server to stop
    await fetch(`${API_BASE}/capture/stop`, { method: 'POST' });
    
    // 2. Clear the local JS interval
    if (previewInterval) {
        clearInterval(previewInterval);
        previewInterval = null;
    }
    
    notify("Preview Stopped", "neutral");
}

document.getElementById('stop-btn').addEventListener('click', stopEverything);

/* ==========================================
   8. PREVIEW MANAGEMENT
   ========================================== */
const HoloScope = {
    previewTimer: null,

    async setMode(mode) {
        // Stop the JS timer immediately
        if (this.previewTimer) {
            clearInterval(this.previewTimer);
            this.previewTimer = null;
        }

        if (mode === 'preview') {
            await fetch('/api/mode/preview', { method: 'POST' });
            this.startPreviewLoop();
        } else {
            await fetch('/api/capture/stop', { method: 'POST' });
        }
    },

    startPreviewLoop() {
        this.previewTimer = setInterval(() => {
            document.getElementById('preview-frame').src = `/api/preview?t=${Date.now()}`;
        }, 3000);
    }
};

// Start Polling
setInterval(updateSensors, 2000);   
setInterval(refreshFiles, 10000);  
refreshFiles();