#!/usr/bin/env python3
"""
Camera Brightness Testing and Adjustment Script
Tests different exposure and gain settings to compensate for camera brightness differences
"""

import cv2
import numpy as np
from picamera2 import Picamera2
import time
import os
from datetime import datetime

# Camera Configuration Matrix
CAMERA_CONFIG = [
    [3, 0], 
    [2, 1] 
]

# Camera labels for overlay text
CAMERA_LABELS = ["Cam 0", "Cam 1", "Cam 2", "Cam 3"]

# Brightness compensation settings - adjust these values to match your cameras
# Based on your observation: 1 (brightest), 0, 3, 2 (darkest)
BRIGHTNESS_COMPENSATION = {
    0: {"exposure_multiplier": 1.0, "gain_multiplier": 1.0},   # Second brightest
    1: {"exposure_multiplier": 0.8, "gain_multiplier": 0.9},   # Brightest - reduce exposure
    2: {"exposure_multiplier": 1.4, "gain_multiplier": 1.2},   # Darkest - increase exposure
    3: {"exposure_multiplier": 1.2, "gain_multiplier": 1.1}    # Second darkest
}

def test_camera_brightness():
    """Test camera brightness with different exposure settings"""
    print("🔧 Starting camera brightness test...")
    
    # Initialize camera
    picam2 = Picamera2()
    
    # Configure camera
    config = picam2.create_preview_configuration(
        main={"size": (2560, 400)},
        controls={
            "ExposureTime": 20000,  # Base exposure time (microseconds)
            "AnalogueGain": 1.0,    # Base gain
            "AeEnable": False,      # Disable auto exposure
            "AwbEnable": False      # Disable auto white balance for consistency
        }
    )
    
    picam2.configure(config)
    picam2.start()
    
    # Wait for camera to stabilize
    time.sleep(2)
    
    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"brightness_test_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📁 Output directory: {output_dir}")
    
    # Test different exposure settings
    exposure_times = [10000, 15000, 20000, 25000, 30000]  # microseconds
    gains = [0.8, 1.0, 1.2, 1.4, 1.6]
    
    for i, exposure in enumerate(exposure_times):
        for j, gain in enumerate(gains):
            print(f"🔍 Testing exposure={exposure}μs, gain={gain}")
            
            # Set camera controls
            picam2.set_controls({
                "ExposureTime": exposure,
                "AnalogueGain": gain
            })
            
            # Wait for settings to take effect
            time.sleep(1)
            
            # Capture image
            filename = f"{output_dir}/test_exp{exposure}_gain{gain:.1f}.jpg"
            picam2.capture_file(filename)
            
            # Also capture and analyze individual cameras
            frame = picam2.capture_array()
            if len(frame.shape) == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Split into individual cameras and analyze brightness
            camera_width = frame.shape[1] // 4
            camera_height = frame.shape[0]
            
            brightnesses = []
            for cam_idx in range(4):
                x_start = cam_idx * camera_width
                x_end = (cam_idx + 1) * camera_width
                camera_frame = frame[0:camera_height, x_start:x_end]
                
                # Calculate average brightness
                brightness = np.mean(camera_frame)
                brightnesses.append(brightness)
                
                # Save individual camera frame
                cam_filename = f"{output_dir}/cam{cam_idx}_exp{exposure}_gain{gain:.1f}.jpg"
                cv2.imwrite(cam_filename, camera_frame)
            
            # Print brightness analysis
            print(f"   Camera brightnesses: {[f'{b:.1f}' for b in brightnesses]}")
            
            # Calculate brightness ratios
            if min(brightnesses) > 0:
                ratios = [b / min(brightnesses) for b in brightnesses]
                print(f"   Brightness ratios: {[f'{r:.2f}' for r in ratios]}")
    
    picam2.stop()
    print(f"✅ Brightness test completed. Results saved in: {output_dir}")
    print(f"📊 Analyze the images to determine optimal settings for each camera.")


def create_brightness_compensated_preview():
    """Create a live preview with brightness compensation applied"""
    print("🚀 Starting brightness-compensated live preview...")
    
    # Initialize camera
    picam2 = Picamera2()
    
    # Configure camera with base settings
    config = picam2.create_preview_configuration(
        main={"size": (2560, 400)},
        controls={
            "ExposureTime": 20000,  # Base exposure time
            "AnalogueGain": 1.0,    # Base gain
            "AeEnable": False,      # Disable auto exposure
            "AwbEnable": False      # Disable auto white balance
        }
    )
    
    picam2.configure(config)
    picam2.start()
    
    # Wait for camera to stabilize
    time.sleep(2)
    
    # Create window
    cv2.namedWindow("Brightness Compensated Preview", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Brightness Compensated Preview", 1280, 400)
    
    print("Controls:")
    print("  'q' - Quit")
    print("  'c' - Capture test image")
    print("  '1'-'4' - Adjust camera 1-4 brightness")
    print("  '+'/'-' - Increase/decrease exposure for selected camera")
    
    selected_camera = 0
    
    try:
        while True:
            # Capture frame
            frame = picam2.capture_array()
            if len(frame.shape) == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Apply software brightness compensation
            compensated_frame = apply_brightness_compensation(frame)
            
            # Display
            cv2.imshow("Brightness Compensated Preview", compensated_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                # Capture test image
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"brightness_compensated_{timestamp}.jpg"
                cv2.imwrite(filename, compensated_frame)
                print(f"📸 Captured: {filename}")
            elif key in [ord('1'), ord('2'), ord('3'), ord('4')]:
                selected_camera = int(chr(key)) - 1
                print(f"🎯 Selected camera {selected_camera}")
            elif key == ord('+'):
                # Increase brightness for selected camera
                BRIGHTNESS_COMPENSATION[selected_camera]["exposure_multiplier"] *= 1.1
                print(f"📈 Camera {selected_camera} brightness increased to {BRIGHTNESS_COMPENSATION[selected_camera]['exposure_multiplier']:.2f}")
            elif key == ord('-'):
                # Decrease brightness for selected camera
                BRIGHTNESS_COMPENSATION[selected_camera]["exposure_multiplier"] *= 0.9
                print(f"📉 Camera {selected_camera} brightness decreased to {BRIGHTNESS_COMPENSATION[selected_camera]['exposure_multiplier']:.2f}")
    
    except KeyboardInterrupt:
        print("\n⏹️  Stopped by user")
    
    finally:
        picam2.stop()
        cv2.destroyAllWindows()
        print("🏁 Preview ended")


def apply_brightness_compensation(frame):
    """Apply brightness compensation to individual camera regions"""
    camera_width = frame.shape[1] // 4
    camera_height = frame.shape[0]
    
    compensated_frame = frame.copy()
    
    for cam_idx in range(4):
        x_start = cam_idx * camera_width
        x_end = (cam_idx + 1) * camera_width
        
        # Extract camera region
        camera_region = frame[0:camera_height, x_start:x_end].copy()
        
        # Get compensation settings
        comp_settings = BRIGHTNESS_COMPENSATION[cam_idx]
        
        # Apply brightness compensation
        brightness_factor = comp_settings["exposure_multiplier"]
        
        # Apply gamma correction for brightness adjustment
        gamma = 1.0 / brightness_factor if brightness_factor > 1.0 else 1.0 + (1.0 - brightness_factor)
        
        # Build lookup table for gamma correction
        lookup_table = np.array([((i / 255.0) ** gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
        
        # Apply gamma correction
        compensated_region = cv2.LUT(camera_region, lookup_table)
        
        # Additional brightness adjustment if needed
        if brightness_factor != 1.0:
            compensated_region = cv2.convertScaleAbs(compensated_region, alpha=brightness_factor, beta=0)
        
        # Put compensated region back
        compensated_frame[0:camera_height, x_start:x_end] = compensated_region
        
        # Add camera label with compensation info
        label = f"{CAMERA_LABELS[cam_idx]} (×{brightness_factor:.2f})"
        cv2.putText(compensated_frame, label, 
                   (x_start + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    return compensated_frame


if __name__ == "__main__":
    print("📷 Camera Brightness Testing and Compensation")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. Test different exposure/gain settings")
        print("2. Live preview with brightness compensation")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            test_camera_brightness()
        elif choice == '2':
            create_brightness_compensated_preview()
        elif choice == '3':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.") 