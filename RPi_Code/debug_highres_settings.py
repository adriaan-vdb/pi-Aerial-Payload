#!/usr/bin/env python3
"""
High-Resolution Calibration Settings Debug Tool
==============================================
This script helps debug where camera settings get lost during high-resolution calibration.
Run this to trace the settings through each step of the process.
"""

import sys
import os
import time
sys.path.append('/home/av/Documents/pi-Aerial-Payload/RPi_Code')

def debug_settings_flow():
    """Debug the settings flow during high-resolution calibration"""
    print("=== High-Resolution Calibration Settings Debug ===")
    print("This tool helps trace where camera settings get lost.")
    print()
    
    print("📋 EXPECTED FLOW:")
    print("1. Web interface sets CAMERA_SETTINGS")
    print("2. High-res calibration starts")
    print("3. calibrate_highres_intrinsics() called")
    print("4. Camera reconfigured for high-res capture")
    print("5. High-res frames captured")
    print("6. Camera restored with CURRENT web interface settings")
    print("7. Main calibration loop starts")
    print("8. capture_calibration_frame() called multiple times")
    print("9. Each frame capture preserves CURRENT web interface settings")
    print("10. Calibration completes")
    print("11. Web interface restores settings")
    print()
    
    print("🔍 WHAT TO CHECK:")
    print("When running High-Res Calibration, look for these debug messages:")
    print()
    
    print("✅ GOOD MESSAGES (settings working):")
    print("   ✓ Using current user settings from web interface: {'exposure_time': 25000, ...}")
    print("   🔧 High-resolution calibration using camera settings: {'ExposureTime': 25000, ...}")
    print("   ✓ Camera configuration restored with current web interface settings: {'ExposureTime': 25000, ...}")
    print("   🔧 Reapplying user camera settings after high-res intrinsics: {'exposure_time': 25000, ...}")
    print("   ✓ Final camera settings verification complete: {'ExposureTime': 25000, ...}")
    print("   ✓ Verified actual camera state - Exposure: 25000, Gain: 2.0")
    print("   ✓ Restored current web interface settings: {'ExposureTime': 25000, ...}")
    print("   ✅ Settings restoration successful! Exposure: 25000")
    print()
    
    print("❌ BAD MESSAGES (settings lost):")
    print("   ⚠️ Using fallback default settings: {'ExposureTime': 10000, ...}")
    print("   ⚠️ Settings mismatch - Expected: 25000, Actual: 10000")
    print("   ⚠️ Warning: Could not apply user camera settings")
    print("   ⚠️ Warning: Settings restoration may not have been fully successful")
    print()
    
    print("🎯 STEPS TO DEBUG:")
    print("1. Set specific camera settings in web interface (e.g., Exposure: 25000)")
    print("2. Note the settings in the camera feed")
    print("3. Click 'High-Res Calibration'")
    print("4. Watch terminal output for the messages above")
    print("5. Check if camera feed maintains same brightness after calibration")
    print()
    
    print("📊 COMPARISON TEST:")
    print("- 'Test Frame' works → settings preserved ✅")
    print("- 'High-Res Calibration' breaks → settings lost ❌")
    print("- The difference is in the high-res intrinsics step")
    print()
    
    return True

def create_settings_test_script():
    """Create a simple test script to check current CAMERA_SETTINGS"""
    test_script = '''#!/usr/bin/env python3
# Quick settings check
import sys
sys.path.append('/home/av/Documents/pi-Aerial-Payload/RPi_Code')

# Import the web interface module to check CAMERA_SETTINGS
try:
    from WebLivePreview_Enhanced import CAMERA_SETTINGS
    print(f"Current CAMERA_SETTINGS: {CAMERA_SETTINGS}")
except ImportError as e:
    print(f"Could not import CAMERA_SETTINGS: {e}")
'''
    
    with open('check_settings.py', 'w') as f:
        f.write(test_script)
    
    print("📝 Created 'check_settings.py' - run this to check current CAMERA_SETTINGS")
    print("   Usage: python3 check_settings.py")

def main():
    """Main debug function"""
    print("High-Resolution Calibration Settings Debug Tool")
    print("=" * 50)
    
    debug_settings_flow()
    create_settings_test_script()
    
    print("=" * 50)
    print("🔧 FIXES APPLIED:")
    print("1. Settings restoration uses current web interface values")
    print("2. Settings reapplied after high-res intrinsics step")
    print("3. Final verification before main calibration loop")
    print("4. Multiple restoration attempts in web interface")
    print("5. Real-time verification of applied settings")
    print()
    print("If settings are still getting lost, the debug messages above")
    print("will help identify exactly where the issue occurs.")

if __name__ == "__main__":
    main() 