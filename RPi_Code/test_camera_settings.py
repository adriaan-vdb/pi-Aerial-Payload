#!/usr/bin/env python3
"""
Camera Settings Test Script
===========================
Tests that camera settings are properly passed from the web interface to the calibration system
"""

import sys
import os
sys.path.append('/home/av/Documents/pi-Aerial-Payload/RPi_Code')

from MultiCameraCalibration_V6 import UnifiedMultiCameraCalibrator

def test_camera_settings_passing():
    """Test that camera settings are properly passed to calibration system"""
    print("=== Testing Camera Settings Passing ===")
    
    # Simulate web interface camera settings
    web_interface_settings = {
        'exposure_time': 20000,
        'analogue_gain': 2.5,
        'contrast': 2.0
    }
    
    print(f"Web interface settings: {web_interface_settings}")
    
    # Create calibrator without external camera (for testing)
    calibrator = UnifiedMultiCameraCalibrator()
    
    # Set the current settings (simulating web interface)
    calibrator.current_settings = web_interface_settings
    
    # Test getting current camera settings
    camera_controls = calibrator.get_current_camera_settings()
    print(f"Camera controls returned: {camera_controls}")
    
    # Verify settings match
    expected_controls = {
        "ExposureTime": 20000,
        "AnalogueGain": 2.5,
        "Contrast": 2.0
    }
    
    success = True
    for key, expected_value in expected_controls.items():
        if key in camera_controls and camera_controls[key] == expected_value:
            print(f"✓ {key}: {camera_controls[key]} (correct)")
        else:
            print(f"✗ {key}: {camera_controls.get(key, 'missing')} (expected: {expected_value})")
            success = False
    
    if success:
        print("✅ Camera settings test PASSED")
    else:
        print("❌ Camera settings test FAILED")
    
    return success

def test_fallback_settings():
    """Test that fallback settings work when no web interface settings provided"""
    print("\n=== Testing Fallback Settings ===")
    
    # Create calibrator without settings
    calibrator = UnifiedMultiCameraCalibrator()
    calibrator.current_settings = None  # No web interface settings
    
    # Test getting fallback settings
    camera_controls = calibrator.get_current_camera_settings()
    print(f"Fallback camera controls: {camera_controls}")
    
    # Expected fallback values
    expected_fallback = {
        "ExposureTime": 10000,
        "AnalogueGain": 1.5,
        "Contrast": 1.2
    }
    
    success = True
    for key, expected_value in expected_fallback.items():
        if key in camera_controls and camera_controls[key] == expected_value:
            print(f"✓ {key}: {camera_controls[key]} (correct fallback)")
        else:
            print(f"✗ {key}: {camera_controls.get(key, 'missing')} (expected: {expected_value})")
            success = False
    
    if success:
        print("✅ Fallback settings test PASSED")
    else:
        print("❌ Fallback settings test FAILED")
    
    return success

def main():
    """Run all camera settings tests"""
    print("Camera Settings Test Suite")
    print("=" * 30)
    
    results = []
    results.append(test_camera_settings_passing())
    results.append(test_fallback_settings())
    
    print("\n" + "=" * 30)
    print("SUMMARY")
    print("=" * 30)
    
    if all(results):
        print("✅ ALL TESTS PASSED")
        print("Camera settings are properly passed from web interface to calibration system")
    else:
        print("❌ SOME TESTS FAILED")
        print("Camera settings passing may have issues")
    
    return all(results)

if __name__ == "__main__":
    main() 