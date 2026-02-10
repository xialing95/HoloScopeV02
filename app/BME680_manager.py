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
        self.sensor = None
        self.i2c = None
        self.reconnect() # Use the new reconnect method to initialize

    def reconnect(self):
        """Attempts to re-initialize the I2C bus and sensor object."""
        try:
            # Clear old references if they exist
            self.sensor = None
            self.i2c = None
            
            # Re-init I2C bus
            self.i2c = board.I2C()
            
            # Try primary address 0x77
            try:
                self.sensor = adafruit_bme680.Adafruit_BME680_I2C(self.i2c, address=0x77)
            except Exception:
                # Fallback to secondary 0x76
                self.sensor = adafruit_bme680.Adafruit_BME680_I2C(self.i2c, address=0x76)
            
            if self.sensor:
                self.sensor.sea_level_pressure = 1013.25
                print("BME680 Reconnected Successfully")
                return True
        except Exception as e:
            print(f"I2C Reconnect Failed: {e}")
            return False
        return False

    def get_readings(self):
        if not self.sensor:
            # Try one auto-reconnect if sensor is missing
            if not self.reconnect():
                return None
        
        try:
            # Accessing temperature triggers the I2C read
            return {
                "temp": round(self.sensor.temperature + self.temp_offset, 2),
                "humidity": round(self.sensor.relative_humidity, 2),
                "pressure": round(self.sensor.pressure, 2),
                "unit_temp": "°C",
                "unit_pressure": "hPa"
            }
        except Exception as e:
            print(f"Error reading sensor: {e}")
            # If a read fails, it's often a bus hang; nulling sensor 
            # forces the UI to show the 'Reconnect' button
            self.sensor = None 
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