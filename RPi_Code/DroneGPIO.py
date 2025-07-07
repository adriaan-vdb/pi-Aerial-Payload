import RPi.GPIO as GPIO 
from picamera2 import Picamera2, Preview
from datetime import datetime
import os

# Ensure GPIO capture directory exists
gpio_captures_dir = "/home/av/Documents/pi-Aerial-Payload/captures/gpio_triggers"
os.makedirs(gpio_captures_dir, exist_ok=True)

picam2 = Picamera2() 
picam2.start()
capture_config = picam2.create_still_configuration()

GPIO.setmode(GPIO.BCM)
GPIO.setup(14, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

prevState = None
capture_count = 0

print("GPIO trigger system started. Waiting for pin 14 signals...")
print(f"Images will be saved to: {gpio_captures_dir}")

try:
    while True:
        inputState = GPIO.input(14)
        if inputState != prevState:
            if inputState == GPIO.HIGH:
                capture_count += 1
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"gpio_trigger_{timestamp}_{capture_count:03d}.jpg"
                filepath = os.path.join(gpio_captures_dir, filename)
                
                print(f"High signal detected - capturing: {filename}")
                picam2.switch_mode_and_capture_file(capture_config, filepath)
            else:
                print("Low signal detected")
            prevState = inputState
except KeyboardInterrupt:
    print(f"\nGPIO trigger system stopped. Captured {capture_count} images.")
    GPIO.cleanup()
    picam2.stop()
    