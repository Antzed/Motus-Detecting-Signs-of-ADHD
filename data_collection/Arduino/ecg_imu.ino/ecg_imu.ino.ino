#include <Adafruit_TinyUSB.h>
#include "LSM6DS3.h"
#include "Wire.h"
#include <U8x8lib.h>  // U8g2 library 

// Pin definitions
const int ecgPin = A0;  // ECG/heart rate sensor on A0

// IMU settings
int IMU_HZ = 100;
int samplesPerSecond = IMU_HZ;

// Display setup
U8X8_SSD1306_128X64_NONAME_HW_I2C u8x8(/* clock=*/PIN_WIRE_SCL, /* data=*/PIN_WIRE_SDA, /* reset=*/U8X8_PIN_NONE);

// Create IMU instance
LSM6DS3 myIMU(I2C_MODE, 0x6A);  // I2C device address 0x6A

// Data transmission format
// For ECG: "ECG,value"
// For IMU: "IMU,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z"

unsigned long lastImuTime = 0;
unsigned long recordCount = 0;

void setup() {
  Serial.begin(115200);  // Higher baud rate for faster data transmission
  
  // Initialize display
  u8x8.begin();
  u8x8.setFlipMode(1);
  u8x8.setFont(u8x8_font_chroma48medium8_r);
  u8x8.clear();
  
  // Initialize LED
  pinMode(LED_BUILTIN, OUTPUT);
  
  // Initialize IMU
  if (myIMU.begin() != 0) {
    Serial.println("IMU initialization error");
  } else {
    Serial.println("IMU initialized successfully");
  }
  
  // Initialize I2C
  Wire.begin();
  
  // Wait for serial connection
  while(!Serial) {
    delay(10);
  }
  
  // Display header
  u8x8.setCursor(0, 0);
  u8x8.print("ECG + IMU Logger");
}

void loop() {
  // Current time
  unsigned long currentTime = millis();
  
  // Read and send ECG data with every loop (fast sampling)
  int ecgValue = analogRead(ecgPin);
  Serial.print("ECG,");
  Serial.println(ecgValue);
  
  // Read and send IMU data at the specified frequency
  if (currentTime - lastImuTime >= (1000 / IMU_HZ)) {
    // Read IMU data
    float accelX = myIMU.readFloatAccelX();
    float accelY = myIMU.readFloatAccelY();
    float accelZ = myIMU.readFloatAccelZ();
    float gyroX = myIMU.readFloatGyroX();
    float gyroY = myIMU.readFloatGyroY();
    float gyroZ = myIMU.readFloatGyroZ();
    
    // Send IMU data
    Serial.print("IMU,");
    Serial.print(accelX, 4); Serial.print(",");
    Serial.print(accelY, 4); Serial.print(",");
    Serial.print(accelZ, 4); Serial.print(",");
    Serial.print(gyroX, 4); Serial.print(",");
    Serial.print(gyroY, 4); Serial.print(",");
    Serial.println(gyroZ, 4);
    
    // Update display
    recordCount++;
    if (recordCount % 20 == 0) {
      u8x8.setCursor(0, 3);
      u8x8.print("ECG+IMU: ");
      u8x8.print(recordCount);
    }
    
    // Blink LED once per second
    if (recordCount % IMU_HZ == 0) {
      digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
    }
    
    // Update last IMU sample time
    lastImuTime = currentTime;
  }
  
  // Small delay to prevent flooding
  delay(2);
}