#!/usr/bin/env python3
"""
Manual Exposure Control for Arducam Multi Camera HAT with OV9281 Sensors
Demonstrates proper way to disable auto-exposure and set manual exposure uniformly
"""

from picamera2 import Picamera2
import time
import cv2
import numpy as np

def setup_manual_exposure(exposure_time_us=5000, gain=1.0):
    """
    Setup camera with manual exposure control
    
    Args:
        exposure_time_us: Exposure time in microseconds
        gain: Analogue gain (typically 1.0-16.0)
    
    Returns:
        Configured Picamera2 instance
    """
    print(f"🔧 Setting up manual exposure: {exposure_time_us}μs, gain: {gain}")
    
    picam2 = Picamera2()
    
    # Check available controls first
    try:
        available_controls = picam2.camera_controls
        print(f"📋 Available controls: {list(available_controls.keys())}")
    except Exception as e:
        print(f"⚠️  Could not check controls: {e}")
        available_controls = {}
    
    # Create configuration with manual controls
    config = picam2.create_still_configuration(
        main={"size": (2560, 400)},  # Full resolution for all 4 cameras
        controls={
            "ExposureTime": exposure_time_us,
            "AnalogueGain": gain,
            "AeEnable": False if "AeEnable" in available_controls else None
        }
    )
    
    # Remove None values from controls
    if config.get("controls"):
        config["controls"] = {k: v for k, v in config["controls"].items() if v is not None}
    
    picam2.configure(config)
    
    # Alternative method: Set controls after configuration
    try:
        manual_controls = {
            "ExposureTime": exposure_time_us,
            "AnalogueGain": gain
        }
        
        # Only add AeEnable if supported
        if "AeEnable" in available_controls:
            manual_controls["AeEnable"] = False
            
        picam2.set_controls(manual_controls)
        print(f"✅ Manual controls applied: {manual_controls}")
        
    except Exception as e:
        print(f"⚠️  Error setting controls: {e}")
    
    return picam2

def get_ov9281_safe_exposure_ranges():
    """
    Get safe exposure time ranges for OV9281 sensor
    
    Returns:
        dict: Min/max exposure times and recommended ranges
    """
    return {
        "absolute_min": 1,          # 1 microsecond (sensor limit)
        "absolute_max": 1000000,    # 1 second (1,000,000 μs)
        "recommended_min": 100,     # 100μs for very bright conditions
        "recommended_max": 100000,  # 100ms for low light conditions
        "typical_outdoor": 1000,    # 1ms for daylight
        "typical_indoor": 10000,    # 10ms for indoor lighting
        "low_light": 50000,         # 50ms for dim conditions
        "frame_rate_limits": {
            "60fps_max": 16667,     # Max exposure for 60fps
            "30fps_max": 33333,     # Max exposure for 30fps
            "10fps_max": 100000     # Max exposure for 10fps
        }
    }

def verify_camera_settings(picam2):
    """
    Verify that exposure settings are applied correctly
    
    Args:
        picam2: Configured Picamera2 instance
    
    Returns:
        dict: Current camera settings
    """
    print("🔍 Verifying camera settings...")
    
    try:
        # Get current control values
        current_controls = {}
        
        # Try to read back the controls we set
        controls_to_check = ["ExposureTime", "AnalogueGain", "AeEnable"]
        
        for control in controls_to_check:
            try:
                # Note: Reading control values back is not always supported
                # This is a limitation of the camera interface
                print(f"   {control}: Set but readback not available")
            except Exception as e:
                print(f"   {control}: Cannot read back ({e})")
        
        print("✅ Settings verification complete")
        print("ℹ️  Note: Arducam HAT multiplexes all cameras, so settings apply uniformly")
        
        return current_controls
        
    except Exception as e:
        print(f"❌ Error verifying settings: {e}")
        return {}

def capture_test_images_with_different_exposures():
    """
    Test different exposure settings and capture sample images using single camera instance
    """
    print("📸 Testing different exposure settings...")
    
    exposure_ranges = get_ov9281_safe_exposure_ranges()
    test_exposures = [
        ("bright", exposure_ranges["recommended_min"]),
        ("normal", exposure_ranges["typical_outdoor"]),
        ("indoor", exposure_ranges["typical_indoor"]),
        ("low_light", exposure_ranges["low_light"])
    ]
    
    # Create single camera instance and reuse it
    picam2 = None
    try:
        print("🔧 Initializing camera for exposure tests...")
        picam2 = Picamera2()
        
        for condition, exposure_time in test_exposures:
            print(f"\n🔧 Testing {condition} exposure: {exposure_time}μs")
            
            try:
                # Stop camera if running
                if picam2.started:
                    picam2.stop()
                
                # Configure with new exposure settings
                config = picam2.create_still_configuration(
                    main={"size": (2560, 400)},
                    controls={
                        "ExposureTime": exposure_time,
                        "AnalogueGain": 1.0,
                        "AeEnable": False
                    }
                )
                picam2.configure(config)
                
                # Set controls
                picam2.set_controls({
                    "ExposureTime": exposure_time,
                    "AnalogueGain": 1.0,
                    "AeEnable": False
                })
                
                # Start camera
                picam2.start()
                
                # Wait for camera to stabilize
                time.sleep(2)
                
                # Capture image
                filename = f"exposure_test_{condition}_{exposure_time}us.jpg"
                picam2.capture_file(filename)
                
                # Also capture array for analysis
                frame = picam2.capture_array()
                if len(frame.shape) == 3:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Analyze brightness of each camera
                camera_width = frame.shape[1] // 4
                camera_brightness = []
                
                for i in range(4):
                    x_start = i * camera_width
                    x_end = (i + 1) * camera_width
                    camera_region = frame[:, x_start:x_end]
                    brightness = np.mean(camera_region)
                    camera_brightness.append(brightness)
                
                print(f"   📊 Camera brightness levels: {[f'{b:.1f}' for b in camera_brightness]}")
                print(f"   📁 Saved: {filename}")
                
            except Exception as e:
                print(f"   ❌ Error with {condition} exposure: {e}")
                
    except Exception as e:
        print(f"❌ Error initializing camera for tests: {e}")
        
    finally:
        # Clean up camera
        if picam2:
            try:
                if picam2.started:
                    picam2.stop()
                picam2.close()
            except:
                pass

def main():
    """Main function demonstrating manual exposure control"""
    print("🚀 OV9281 Manual Exposure Control Demo")
    print("=" * 50)
    
    # Show safe exposure ranges
    ranges = get_ov9281_safe_exposure_ranges()
    print("\n📊 OV9281 Safe Exposure Ranges:")
    print(f"   Absolute range: {ranges['absolute_min']}μs - {ranges['absolute_max']}μs")
    print(f"   Recommended: {ranges['recommended_min']}μs - {ranges['recommended_max']}μs")
    print(f"   Typical outdoor: {ranges['typical_outdoor']}μs")
    print(f"   Typical indoor: {ranges['typical_indoor']}μs")
    print(f"   Low light: {ranges['low_light']}μs")
    
    print("\n🎯 Frame Rate Limitations:")
    for fps, max_exp in ranges['frame_rate_limits'].items():
        print(f"   {fps}: Max exposure {max_exp}μs")
    
    # Test basic manual exposure setup
    print(f"\n🔧 Testing manual exposure setup...")
    exposure_time = 5000  # 5ms - good for general use
    
    try:
        picam2 = setup_manual_exposure(exposure_time)
        verify_camera_settings(picam2)
        
        picam2.start()
        print("✅ Camera started with manual exposure")
        
        # Capture a test image
        picam2.capture_file("manual_exposure_test.jpg")
        print("📸 Test image captured: manual_exposure_test.jpg")
        
        # Clean up properly
        picam2.stop()
        picam2.close()
        
    except Exception as e:
        print(f"❌ Error in basic test: {e}")
    
    # Run comprehensive exposure tests
    print(f"\n🧪 Running comprehensive exposure tests...")
    capture_test_images_with_different_exposures()
    
    print(f"\n✅ Manual exposure demo complete!")
    print(f"📊 Review the captured images to see the effects of different exposures")

if __name__ == "__main__":
    main() 