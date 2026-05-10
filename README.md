# ECE-528-Final-Project
Final project files relating to project.

# Project Overview
Project involves the programming of a lidar sensor and utilizing its gathered data values to output visualizations. 

# System Architecture
The project utilizes the ESP32-S3-DevKitC1 MCU to interact with the TF-Luna LiDAR sensor.
The lidar sensor will send over data bytes through UART protocol to the ESP32. 
Then the ESP32 will send over the serial data to the PC so that C++ and python can work together to process the received data address and create visualizations.

# Interfaces and Peripherals Used
Pins:
  GPIO 16
  GPIO 17
  3V3
  GND
  
Components:
  ESP32-S3-DevKitC1
  TF-Luna LiDAR
  USB-C Cable
  Laptop or equivalent PC

# Verification and Testing
Hardware:
  RGB leds on the ESP32 are to be verified upon connection to an outside power source since the MCU has no built in power source of its own.
  Making sure the connections on the TF-Luna were properly connected otherwise the internal IR sensor would not be energized.

Software:
  Verifying that the serial monitor terminal is properly outputting the serial data it's receiving with the intended COM port and baud rate.
  And additional verification that the data is being plotted on the graphs.

# Project Demonstration
Project was demonstrated live during presentation.

# Conclusion
In conclusion, the TF-Luna lidar was successfully energized and was able to transmit over UART data to the ESP32 which would then be transmitted to the laptop/PC.
With a constant multitude of live data points coming in, the graphs were able to successfully show the live data that the lidar sensor was generating.
It goes to show how even one sensor has a valuable amount of data that can be used to visualize and apply over different environments.
