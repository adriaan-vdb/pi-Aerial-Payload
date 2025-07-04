
import RPi.GPIO as GPIO 
from picamera2 import Picamera2, Preview
from datetime import datetime

picam2 = Picamera2() 
picam2.start()
capture_config = picam2.create_still_configuration()


GPIO.setmode(GPIO.BCM)

GPIO.setup(14, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
prevState = None
try:
    while True:
        inputState = GPIO.input(14)
        if inputState != prevState:
            if inputState == GPIO.HIGH:
                print("high")
                picam2.switch_mode_and_capture_file(capture_config, "high.jpg" )
            else:
                print("low")
            prevState = inputState
except KeyboardInterrupt:
    GPIO.cleanup()
    