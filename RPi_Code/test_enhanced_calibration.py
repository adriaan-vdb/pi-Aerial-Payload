#!/usr/bin/env python3
"""
Enhanced Multi-Camera Calibration Test Script
============================================
Demonstrates the new features:
1. Global bundle adjustment
2. High-resolution intrinsic calibration
3. Automated quality validation
"""

import sys
import os
sys.path.append('/home/av/Documents/pi-Aerial-Payload/RPi_Code')

from MultiCameraCalibration_V6 import UnifiedMultiCameraCalibrator
import time

def test_standard_calibration():
    """Test standard calibration with bundle adjustment"""
    print("=== Testing Standard Calibration with Bundle Adjustment ===")
    
    calibrator = UnifiedMultiCameraCalibrator()
    
    # Run standard calibration (includes bundle adjustment)
    success = calibrator.perform_full_calibration(target_frames=15)
    
    if success:
        print("✅ Standard calibration completed successfully")
        
        # Check if bundle adjustment was performed
        if hasattr(calibrator, 'bundle_adjustment_performed'):
            print("✅ Bundle adjustment was performed")
        else:
            print("ℹ️  Bundle adjustment may have been skipped")
    else:
        print("❌ Standard calibration failed")
    
    return success

def test_highres_calibration():
    """Test high-resolution intrinsic calibration"""
    print("\n=== Testing High-Resolution Intrinsic Calibration ===")
    
    calibrator = UnifiedMultiCameraCalibrator()
    
    # Run high-resolution calibration
    success = calibrator.perform_full_calibration(target_frames=15, use_highres_intrinsics=True)
    
    if success:
        print("✅ High-resolution calibration completed successfully")
        
        # Check if high-res intrinsics were used
        if calibrator.use_highres_intrinsics:
            print("✅ High-resolution intrinsics were used")
        else:
            print("ℹ️  Fell back to standard intrinsics")
    else:
        print("❌ High-resolution calibration failed")
    
    return success

def test_quality_validation():
    """Test automated quality validation"""
    print("\n=== Testing Automated Quality Validation ===")
    
    # Check if validation results exist
    validation_file = "/home/av/Documents/pi-Aerial-Payload/maps/rectification_validation.json"
    
    if os.path.exists(validation_file):
        import json
        with open(validation_file, 'r') as f:
            validation_results = json.load(f)
        
        print("✅ Quality validation results found")
        print(f"Overall quality: {'GOOD' if validation_results['overall_quality'] else 'POOR'}")
        
        for pair_name, results in validation_results['pair_results'].items():
            quality_str = "GOOD" if results['quality_good'] else "POOR"
            print(f"  Pair {pair_name}: {quality_str}")
            print(f"    Mean vertical disparity: {results['mean_vertical_disparity']:.2f} px")
            print(f"    Max vertical disparity: {results['max_vertical_disparity']:.2f} px")
            print(f"    Features matched: {results['num_matches']}")
        
        return validation_results['overall_quality']
    else:
        print("❌ No quality validation results found")
        return False

def performance_benchmark():
    """Benchmark the enhanced calibration performance"""
    print("\n=== Performance Benchmark ===")
    
    start_time = time.time()
    calibrator = UnifiedMultiCameraCalibrator()
    
    # Run calibration with timing
    success = calibrator.perform_full_calibration(target_frames=20)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"Total calibration time: {total_time:.1f} seconds")
    
    if total_time < 90:
        print("✅ Performance target met (< 90 seconds)")
    else:
        print("⚠️  Performance target missed (> 90 seconds)")
    
    return success and total_time < 90

def main():
    """Run all tests"""
    print("Enhanced Multi-Camera Calibration Test Suite")
    print("=" * 50)
    
    results = {
        'standard_calibration': False,
        'highres_calibration': False,
        'quality_validation': False,
        'performance_benchmark': False
    }
    
    try:
        # Test 1: Standard calibration with bundle adjustment
        results['standard_calibration'] = test_standard_calibration()
        
        # Test 2: High-resolution intrinsic calibration
        results['highres_calibration'] = test_highres_calibration()
        
        # Test 3: Quality validation
        results['quality_validation'] = test_quality_validation()
        
        # Test 4: Performance benchmark
        results['performance_benchmark'] = performance_benchmark()
        
    except Exception as e:
        print(f"❌ Test suite failed with error: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    all_passed = all(results.values())
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 