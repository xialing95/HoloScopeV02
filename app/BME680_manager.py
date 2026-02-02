import bme680
import time
import os
from datetime import datetime

class SensorManager:
    def __init__(self, temp_offset=-2.5):
        self.temp_offset = temp_offset  # Adjust this to calibrate
        try:
            # Try primary I2C address (0x77) or secondary (0x76)
            self.sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
        except (RuntimeError, IOError):
            self.sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

        # Oversampling settings: Higher = more accurate but slower/more power
        self.sensor.set_humidity_oversample(bme680.OS_2X)
        self.sensor.set_pressure_oversample(bme680.OS_4X)
        self.sensor.set_temperature_oversample(bme680.OS_8X)
        
        # An IIR filter helps smooth out sudden noise from air currents
        self.sensor.set_filter(bme680.FILTER_SIZE_3)

        # Explicitly disable gas measurement to save power and reduce heat
        self.sensor.set_gas_status(bme680.DISABLE_GAS_MEAS)

    def get_readings(self):
        if self.sensor.get_sensor_data():
            return {
                "temp": round(self.sensor.data.temperature + self.temp_offset, 2),
                "humidity": round(self.sensor.data.humidity, 2),
                "pressure": round(self.sensor.data.pressure, 2),
                "unit_temp": "°C",
                "unit_pressure": "hPa"
            }
        return None
    
    def _logging_worker(self):
        """Background thread that writes BME680 data to a unique timestamped CSV."""
        log_dir = "/home/pi/HoloScopeV02/data"
        os.makedirs(log_dir, exist_ok=True)
        
        # 1. Generate a unique filename for this logging session
        session_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"sensor_log_{session_ts}.csv")
        
        print(f"BME680 Logging Session Started: {log_file}")

        while self.log_enabled:
            data = sensors.get_readings() 
            
            if data:
                # Check if file exists to decide if we need a header
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
            
            # Sleep in 1s chunks to stay responsive to "Stop" signals
            for _ in range(self.log_interval):
                if not self.log_enabled:
                    break
                time.sleep(1)
        
        print("BME680 Logging Session Stopped.")

# Global instance for use in FastAPI
sensors = SensorManager(temp_offset=-2.0)