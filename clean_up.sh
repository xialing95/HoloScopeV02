# 1. Stop the running service
sudo systemctl stop holoscope.service

# 2. Prevent it from starting on boot
sudo systemctl disable holoscope.service

# 3. Remove the service file itself
sudo rm /etc/systemd/system/holoscope.service

# 4. Reload the manager to "forget" the service exists
sudo systemctl daemon-reload

# 5. Reset the failed state (optional, cleans up logs)
sudo systemctl reset-failed

# Remove the HoloScope project directory
if [ -d "$HOME/HoloScope" ]; then
    echo "🗑️ Removing HoloScope project folder..."
    rm -rf "$HOME/HoloScope"
fi

# Remove the capture_image directory (adjust path if it's elsewhere)
if [ -d "$HOME/capture_image" ]; then
    echo "📸 Removing capture_image folder..."
    rm -rf "$HOME/capture_image"
fi