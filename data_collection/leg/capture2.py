import serial
import time
import datetime
import os
import sys

# Serial port settings
port = '/dev/cu.usbmodem101'  # Change this to your Arduino port
baudrate = 115200  # Match this with your Arduino sketch

# File settings
ecg_filename = f"ecg_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
imu_filename = f"imu_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

def get_formatted_timestamp():
    """Generate a timestamp in the same format as the gaze tracking"""
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

def main():
    print(f"Starting data collection from {port} at {baudrate} baud")
    
    try:
        # Open the serial port
        ser = serial.Serial(port, baudrate, timeout=1)
        print("Serial port opened successfully")
        
        # Wait for the serial connection to initialize
        time.sleep(2)
        
        # Create and open both CSV files
        with open(ecg_filename, 'w') as ecg_file, open(imu_filename, 'w') as imu_file:
            # Write CSV headers
            ecg_file.write('timestamp,ecg_value\n')
            imu_file.write('timestamp,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z\n')
            
            print(f"ECG data will be saved to: {ecg_filename}")
            print(f"IMU data will be saved to: {imu_filename}")
            print("Press Ctrl+C to stop data collection")
            
            # Data statistics
            ecg_count = 0
            imu_count = 0
            last_stats_time = time.time()
            
            while True:
                if ser.in_waiting > 0:
                    # Read a line from the serial input
                    line = ser.readline().decode('utf-8').strip()
                    
                    # Get current timestamp
                    timestamp = get_formatted_timestamp()
                    
                    # Process the line based on the data type
                    try:
                        parts = line.split(',')
                        
                        if parts[0] == "ECG" and len(parts) == 2:
                            # Process ECG data
                            ecg_value = int(parts[1])
                            
                            # Create the CSV line with timestamp
                            csv_line = f"{timestamp},{ecg_value}"
                            
                            # Write to ECG CSV file
                            ecg_file.write(csv_line + '\n')
                            ecg_file.flush()  # Ensure data is written immediately
                            
                            ecg_count += 1
                        
                        elif parts[0] == "IMU" and len(parts) == 7:
                            # Process IMU data
                            accel_x = float(parts[1])
                            accel_y = float(parts[2])
                            accel_z = float(parts[3])
                            gyro_x = float(parts[4])
                            gyro_y = float(parts[5])
                            gyro_z = float(parts[6])
                            
                            # Create the CSV line with timestamp
                            csv_line = f"{timestamp},{accel_x},{accel_y},{accel_z},{gyro_x},{gyro_y},{gyro_z}"
                            
                            # Write to IMU CSV file
                            imu_file.write(csv_line + '\n')
                            imu_file.flush()  # Ensure data is written immediately
                            
                            imu_count += 1
                        
                        # Print statistics every second
                        current_time = time.time()
                        if current_time - last_stats_time >= 1.0:
                            print(f"Records collected - ECG: {ecg_count}, IMU: {imu_count}")
                            last_stats_time = current_time
                        
                    except (ValueError, IndexError) as e:
                        # Skip invalid data
                        print(f"Skipping invalid data: {line}")
                        print(f"Error: {e}")
                
                # Brief pause to reduce CPU usage
                time.sleep(0.001)
                
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return
    except KeyboardInterrupt:
        print("\nData collection stopped by user")
    finally:
        # Make sure to close the serial port
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed")
        
        print(f"ECG data saved to {ecg_filename}")
        print(f"IMU data saved to {imu_filename}")

if __name__ == "__main__":
    main()