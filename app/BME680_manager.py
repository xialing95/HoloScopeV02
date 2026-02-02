import time
import os
import csv
import board
import adafruit_bme680
from datetime import datetime

class SensorManager:
    def __init__(self, temp_offset=-2.5):
        self.temp_offset = temp_offset
        self.log_enabled = False
        self.log_interval = 60
        
        try:
            # Initialize I2C bus
            i2c = board.I2C()  # uses board.SCL and board.SDA
            # Initialize sensor (default address is 0x77)
            self.sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x77)
        except Exception as e:
            try:
                # Fallback to secondary address 0x76
                self.sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x76)
            except Exception as e2:
                print(f"Could not find BME680 sensor: {e2}")
                self.sensor = None

        if self.sensor:
            # Sea level pressure for altitude calculation (optional)
            self.sensor.sea_level_pressure = 1013.25
            # In the Adafruit library, gas is disabled by default unless you call it

    def get_readings(self):
        if not self.sensor:
            return None
        
        try:
            return {
                "temp": round(self.sensor.temperature + self.temp_offset, 2),
                "humidity": round(self.sensor.relative_humidity, 2),
                "pressure": round(self.sensor.pressure, 2),
                "unit_temp": "°C",
                "unit_pressure": "hPa"
            }
        except Exception as e:
            print(f"Error reading sensor: {e}")
            return None
    
    def _logging_worker(self):
        """Background thread that writes data to a unique timestamped CSV."""
        log_dir = "/home/pi/HoloScopeV02/data"
        os.makedirs(log_dir, exist_ok=True)
        
        session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"sensor_log_{session_ts}.csv")
        
        print(f"BME680 Logging Session Started: {log_file}")

        while self.log_enabled:
            data = self.get_readings() # Changed to use self
            
            if data:
                file_exists = os.path.isfile(log_file)
                try:
                    with open(log_file, "a", newline="") as f:
                        writer = csv.writer(f)
                        if not file_exists:
                            writer.writerow(["Timestamp", "Temperature_C", "Humidity_Pct", "Pressure_hPa"])
                        
                        writer.writerow([
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            data["temp"],
                            data["humidity"],
                            data["pressure"]
                        ])
                except Exception as e:
                    print(f"Logging error: {e}")
            
            for _ in range(self.log_interval):
                if not self.log_enabled:
                    break
                time.sleep(1)
        
        print("BME680 Logging Session Stopped.")

# Global instance
sensors = SensorManager(temp_offset=-2.0)