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

    // 6. Network
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
                        <a href="${API_BASE}/download/${fileName}" class="btn-small btn-green" download>↓</a>
                        <button class="btn-small btn-red delete-btn" data-filename="${fileName}">x</button>                    
                    </div>
                `;
                fileList.appendChild(fileItem);
            });
            // ATTACH LISTENERS: Link the new buttons to your deleteFile function
            fileList.querySelectorAll('.delete-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const fname = btn.getAttribute('data-filename');
                    deleteFile(fname); // Calling your existing function
                });
            });
        }
    } catch (err) {
        notify("Failed to load gallery", "error");
        console.error(err);
    } finally {
        refreshBtn.disabled = false;
        refreshBtn.innerText = "Refresh Gallery";
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

async function deleteAllFiles() {
    const confirmWipe = confirm("ARE YOU SURE? This will permanently delete EVERY file in the data folder.");
    if (!confirmWipe) return;

    try {
        const response = await fetch(`${API_BASE}/api/files/delete-all`, { method: 'DELETE' });
        if (response.ok) {
            notify("Data folder cleared", "success");
            refreshFiles(); // Update the UI
        }
    } catch (err) {
        notify("Failed to clear folder", "error");
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
        const response = await fetch(`${API_BASE}/api/network`, {
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
        burst_gap: parseInt(document.getElementById('burst-gap').value)
    };

    if (!payload.project_name) return notify("Name required!", "error");
    if (payload.interval < 2) return notify("Min interval is 2s", "error");
    if (!payload.burst_count) return notify("Number of photos required!", "error");


    notify(`Project ${payload.project_name} started...`, "success");

    const response = await fetch(`${API_BASE}/api/capture/burst`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    if (response.ok) {
        notify("Burst Active - Preview Paused", "success");
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

// Start Polling
setInterval(updateSensors, 2000);   
// Run once on page load
refreshFiles();
