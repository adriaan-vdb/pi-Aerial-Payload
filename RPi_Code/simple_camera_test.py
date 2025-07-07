#!/usr/bin/env python3
"""
Simple headless camera test script for QuadCam
Tests camera functionality without requiring VNC or GUI
"""

import time
import os
from datetime import datetime
from picamera2 import Picamera2

def test_camera_capture():
    """Test camera capture without GUI preview"""
    print("🚀 Starting QuadCam headless test...")
    
    try:
        # Initialize camera
        print("📷 Initializing camera...")
        picam2 = Picamera2()
        
        # Create capture configuration for the 4-camera setup
        # The ArduCAM setup typically outputs 2560x400 (4 cameras at 640x400 each)
        capture_config = picam2.create_still_configuration(
            main={"size": (2560, 400)},
            lores={"size": (640, 100)},
            display="lores"
        )
        
        picam2.configure(capture_config)
        
        # Start camera (without preview)
        print("🔧 Starting camera...")
        picam2.start()
        
        # Wait for camera to stabilize
        print("⏳ Waiting for camera to stabilize...")
        time.sleep(3)
        
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"camera_test_{timestamp}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Capture multiple test images
        print("📸 Capturing test images...")
        for i in range(3):
            filename = f"{output_dir}/quadcam_test_{i+1}.jpg"
            print(f"   Capturing image {i+1}/3: {filename}")
            picam2.capture_file(filename)
            time.sleep(1)
        
        # Stop camera
        picam2.stop()
        
        print("✅ Camera test completed successfully!")
        print(f"📁 Images saved in: {output_dir}/")
        print(f"🖼️  Expected image size: 2560x400 pixels (4 cameras combined)")
        
        # List captured files
        files = os.listdir(output_dir)
        for file in files:
            file_path = os.path.join(output_dir, file)
            size = os.path.getsize(file_path)
            print(f"   📄 {file} ({size/1024:.1f} KB)")
            
    except Exception as e:
        print(f"❌ Error during camera test: {e}")
        print("🔍 This might help debug the issue:")
        print("   - Check camera connections")
        print("   - Verify ArduCAM HAT is properly seated")
        print("   - Run: libcamera-still -t 3000 -n -o test.jpg")

if __name__ == "__main__":
    test_camera_capture() 