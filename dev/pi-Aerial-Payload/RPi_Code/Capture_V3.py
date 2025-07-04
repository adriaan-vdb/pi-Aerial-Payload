import time
import os
import sys

# Try to import camera dependencies with error handling
try:
    from picamera2 import Picamera2, Preview
    CAMERA_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Camera dependencies not available: {e}")
    print("This could be due to:")
    print("- Missing libcamera installation")
    print("- Missing picamera2 installation")
    print("- Running on a system without camera support")
    CAMERA_AVAILABLE = False

def check_camera_availability():
    """Check if cameras are available and accessible"""
    if not CAMERA_AVAILABLE:
        return False, "Camera dependencies not installed"
    
    try:
        # Try to get camera information
        camera_info = Picamera2.global_camera_info()
        if not camera_info:
            return False, "No cameras detected"
        
        print(f"Found {len(camera_info)} camera(s):")
        for i, info in enumerate(camera_info):
            print(f"  Camera {i}: {info}")
        
        return True, f"Found {len(camera_info)} camera(s)"
    
    except Exception as e:
        return False, f"Error checking cameras: {e}"

def picamCapture(batch):
    """Capture images from camera with proper error handling"""
    # Check camera availability first
    camera_available, message = check_camera_availability()
    if not camera_available:
        print(f"Error: {message}")
        print("Cannot proceed with image capture.")
        return False
    
    print(f"Camera check passed: {message}")
    
    try:
        # Initialize camera
        print("Initializing camera...")
        picam2 = Picamera2()
        
        # Configure camera
        preview_config = picam2.create_preview_configuration(main={"size": (2560, 400)})
        picam2.configure(preview_config)
        capture_config = picam2.create_still_configuration()

        # Start preview and camera
        print("Starting camera preview...")
        picam2.start_preview(Preview.QTGL)
        picam2.start()
        
        # Create directory for saving images
        directoryPath = f"/home/a22498729/Desktop/Picam/Batch{batch}"
        if not os.path.exists(directoryPath):
            os.makedirs(directoryPath)
            print(f"Created directory: {directoryPath}")
        
        # Optional camera settings
        #picam2.set_controls({"ExposureTime":50000, "AnalogueGain" :0.7})
        
        print("Camera ready. Press Enter to start capture sequence...")
        input()
        
        print("Starting capture sequence in 10 seconds...")
        time.sleep(10)
        
        # Capture images
        for i in range(10):
            try:
                print(f"Capturing image {i+1}/10...")
                picam2.switch_mode_and_capture_file(capture_config, f"{directoryPath}/img{i}.png")
                print(f"Saved: img{i}.png")
                time.sleep(3)
            except Exception as e:
                print(f"Error capturing image {i}: {e}")
                continue
        
        # Clean up
        picam2.stop()
        picam2.close()
        print("Images captured successfully!")
        return True
        
    except Exception as e:
        print(f"Error during camera operation: {e}")
        try:
            picam2.stop()
            picam2.close()
        except:
            pass
        return False

def main():
    """Main function with error handling"""
    print("QuadCam Capture V3 - Starting...")
    
    if not CAMERA_AVAILABLE:
        print("\n=== CAMERA SYSTEM NOT AVAILABLE ===")
        print("To fix this issue:")
        print("1. Install libcamera: sudo apt install libcamera-dev")
        print("2. Install picamera2: pip install picamera2")
        print("3. Enable camera interface: sudo raspi-config → Interface Options → Camera")
        print("4. Make sure you're running on a Raspberry Pi with camera support")
        sys.exit(1)
    
    # Attempt to capture images
    success = picamCapture(3)
    
    if success:
        print("✓ Capture completed successfully!")
        sys.exit(0)
    else:
        print("✗ Capture failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()