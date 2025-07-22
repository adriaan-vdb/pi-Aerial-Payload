#!/usr/bin/env python3
"""
Quick Calibration Verification Runner
====================================
Simple script to run visual calibration verification directly.
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from CalibrationVisualVerification import CalibrationVisualVerifier

def main():
    print("🔍 Running Calibration Visual Verification")
    print("=========================================")
    
    try:
        verifier = CalibrationVisualVerifier()
        verifier.run_verification()
        print("\n✅ Verification complete!")
        print("📁 Check the verification_images folder for results")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("Make sure you've run calibration first!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        try:
            verifier.stop()
        except:
            pass

if __name__ == "__main__":
    main() 