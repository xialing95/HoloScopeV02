import time
from picamera2 import Picamera2

# 1. Initialize Picamera2
picam2 = Picamera2()

# 2. Configure for 10-bit Packed Raw (14.9MB mode)
# 'SRGGB10_CSI2P' is the specific format for 10-bit packed data
config = picam2.create_still_configuration(
    raw={"format": "SRGGB10_CSI2P", "size": (4608, 2592)}
)
picam2.configure(config)
picam2.start()

print("Camera warming up...")
time.sleep(2) # Allow AGC/AWB to settle

# 3. Capture the Raw Buffer
# We do NOT use make_dng=True here because that converts it to the 24MB format
# Instead, we capture the 'raw' stream directly to a file
output_file = "experiment_data.raw"
picam2.capture_file(output_file, stream_name="raw")

print(f"Capture complete. File saved as {output_file}")
import os
print(f"Verified File Size: {os.path.getsize(output_file) / 1e6:.2f} MB")

picam2.stop()