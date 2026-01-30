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
                    <button class="btn-warn" onclick="deleteFile('${file}')" style="width:auto; padding:5px 10px;">×</button>
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
   4. SETTINGS & LOGGING
   ========================================== */
async function saveConfig() {
    notify("Saving configuration...", "neutral");
    
    const payload = {
        project_name: document.getElementById('proj-name').value,
        timelapse_interval_sec: parseInt(document.getElementById('time-interval').value),
        log_interval: parseInt(document.getElementById('log-interval').value),
        log_enabled: document.getElementById('log-enabled').checked,
        shutter_speed: parseInt(document.getElementById('shutter').value),
        iso: parseInt(document.getElementById('iso').value)
    };

    try {
        const response = await fetch(`${API_BASE}/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            notify("Configuration Saved!", "success");
        } else {
            throw new Error("Server rejected settings");
        }
    } catch (err) {
        notify(`Save Failed: ${err.message}`, "error");
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
   6. INITIALIZATION & LOOPS
   ========================================== */
document.getElementById('save-settings-btn').addEventListener('click', saveConfig);
document.getElementById('save-log-btn').addEventListener('click', saveConfig);

document.getElementById('burst-btn').onclick = async () => {
    notify("Triggering Capture...", "neutral");
    try {
        const res = await fetch(`${API_BASE}/burst`, { method: 'POST' });
        if (res.ok) {
            notify("Capture Complete", "success");
            refreshFiles();
        } else {
            throw new Error("Camera Busy");
        }
    } catch (err) {
        notify(`Camera Error: ${err.message}`, "error");
    }
};

// Start Polling
setInterval(updateSensors, 2000);   
setInterval(refreshFiles, 10000);  
refreshFiles();