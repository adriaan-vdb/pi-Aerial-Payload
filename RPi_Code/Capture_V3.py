import time
from picamera2 import Picamera2, Preview
import os
def picamCapture(batch):
    picam2 = Picamera2()
    preview_config = picam2.create_preview_configuration(main={"size": (2560, 400)})
    picam2.configure(preview_config)
    capture_config = picam2.create_still_configuration()

    picam2.start_preview(Preview.OPENCV)
    picam2.start()

    directoryPath = f"/home/av/Documents/pi-Aerial-Payload/captures/Batch{batch}"
    if not os.path.exists(directoryPath):
        os.makedirs(directoryPath)
    '''if  os.path.exists(directoryPath):
        i = i+1
        directoryPath = f"/home/av/Documents/pi-Aerial-Payload/captures/Batch{i}"
        os.makedirs(directoryPath)'''

    #picam2.set_controls({"ExposureTime":50000, "AnalogueGain" :0.7})
    print("abt to take photo")
    input()
    time.sleep(10)
    for i in range(10):
        print("taking image_%s" %i)
        time.sleep(3)
        picam2.switch_mode_and_capture_file(capture_config, f"{directoryPath}/img{i}.png")

picamCapture(3)
print("images captured :)")