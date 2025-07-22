#!/usr/bin/env python3
"""
Calibration Visual Verification Tool
====================================
Creates colored transparent overlays of rectified camera images to visually verify
calibration quality. Perfect calibration = perfect alignment in overlapping regions.
"""

import cv2
import numpy as np
import os
from picamera2 import Picamera2
import time
from datetime import datetime

class CalibrationVisualVerifier:
    def __init__(self):
        self.camera = None
        self.rectification_maps = {}
        self.camera_colors = {
            0: (255, 0, 0),    # Red
            1: (0, 255, 0),    # Green  
            2: (0, 0, 255),    # Blue
            3: (255, 255, 0)   # Yellow/Cyan
        }
        self.transparency = 0.6  # 60% opacity
        
        # Calibration directories
        self.maps_dir = "/home/av/Documents/pi-Aerial-Payload/maps"
        self.output_dir = "/home/av/Documents/pi-Aerial-Payload/verification_images"
        
        # Create output directory
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        self.setup_camera()
        self.load_rectification_maps()
    
    def setup_camera(self):
        """Initialize camera with current settings"""
        try:
            self.camera = Picamera2()
            
            # Use standard settings for verification
            controls = {
                "ExposureTime": 25000,
                "AnalogueGain": 4.0,
                "Contrast": 3.0
            }
            
            config = self.camera.create_still_configuration(
                main={"size": (2560, 400)},
                controls=controls
            )
            self.camera.configure(config)
            self.camera.start()
            time.sleep(0.5)  # Allow camera to stabilize
            
            print("Camera initialized for verification")
            
        except Exception as e:
            print(f"Error initializing camera: {e}")
    
    def load_rectification_maps(self):
        """Load rectification maps from calibration"""
        print("Loading rectification maps...")
        
        # Define stereo pairs based on camera layout
        stereo_pairs = [
            (0, 3),  # Top row horizontal
            (1, 2),  # Bottom row horizontal  
            (0, 1),  # Left column vertical
            (3, 2),  # Right column vertical
        ]
        
        for cam1, cam2 in stereo_pairs:
            map_file = f"{self.maps_dir}/unified_stereoMap_{cam1}{cam2}.xml"
            
            if os.path.exists(map_file):
                # Read rectification maps
                cv_file = cv2.FileStorage(map_file, cv2.FILE_STORAGE_READ)
                
                if cv_file.isOpened():
                    map1_x = cv_file.getNode('stereoMap1_x').mat()
                    map1_y = cv_file.getNode('stereoMap1_y').mat()
                    map2_x = cv_file.getNode('stereoMap2_x').mat()
                    map2_y = cv_file.getNode('stereoMap2_y').mat()
                    
                    self.rectification_maps[f"{cam1}-{cam2}"] = {
                        'map1_x': map1_x, 'map1_y': map1_y,
                        'map2_x': map2_x, 'map2_y': map2_y
                    }
                    
                    print(f"✓ Loaded rectification maps for cameras {cam1}-{cam2}")
                    cv_file.release()
                else:
                    print(f"✗ Could not open {map_file}")
            else:
                print(f"✗ Rectification map not found: {map_file}")
        
        if not self.rectification_maps:
            print("⚠ No rectification maps found! Run calibration first.")
    
    def split_camera_frame(self, frame):
        """Split combined 4-camera frame into individual cameras"""
        if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        camera_width = frame.shape[1] // 4
        camera_height = frame.shape[0]
        
        cameras = {}
        for i in range(4):
            x_start = i * camera_width
            x_end = (i + 1) * camera_width
            cameras[i] = frame[0:camera_height, x_start:x_end].copy()
        
        return cameras
    
    def rectify_camera_pair(self, cam1_img, cam2_img, pair_name):
        """Apply rectification to a camera pair"""
        if pair_name not in self.rectification_maps:
            return None, None
        
        maps = self.rectification_maps[pair_name]
        
        # Apply rectification
        rectified1 = cv2.remap(cam1_img, maps['map1_x'], maps['map1_y'], cv2.INTER_LINEAR)
        rectified2 = cv2.remap(cam2_img, maps['map2_x'], maps['map2_y'], cv2.INTER_LINEAR)
        
        return rectified1, rectified2
    
    def create_colored_overlay(self, image, color, alpha=0.6):
        """Create a colored transparent overlay of the image"""
        # Convert to color if grayscale
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        
        # Create colored version
        colored = np.zeros_like(image)
        colored[:, :] = color
        
        # Apply color with image as mask (where image is bright, color is visible)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mask = gray > 50  # Only show color where there's actual image content
        
        result = image.copy()
        result[mask] = cv2.addWeighted(image[mask], 1-alpha, colored[mask], alpha, 0)
        
        return result
    
    def create_alignment_verification(self, cam1_img, cam2_img, cam1_id, cam2_id, pair_name):
        """Create alignment verification image for a camera pair"""
        # Rectify the pair
        rect1, rect2 = self.rectify_camera_pair(cam1_img, cam2_img, pair_name)
        
        if rect1 is None or rect2 is None:
            print(f"Could not rectify camera pair {cam1_id}-{cam2_id}")
            return None
        
        # Create colored overlays
        color1 = self.camera_colors[cam1_id]
        color2 = self.camera_colors[cam2_id]
        
        overlay1 = self.create_colored_overlay(rect1, color1, self.transparency)
        overlay2 = self.create_colored_overlay(rect2, color2, self.transparency)
        
        # Combine overlays
        combined = cv2.addWeighted(overlay1, 0.5, overlay2, 0.5, 0)
        
        # Add epipolar lines for verification
        h, w = combined.shape[:2]
        for y in range(0, h, 40):  # Every 40 pixels
            cv2.line(combined, (0, y), (w, y), (255, 255, 255), 1, cv2.LINE_AA)
        
        # Add labels
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(combined, f"Cam {cam1_id} (Red) + Cam {cam2_id} ({['', 'Green', 'Blue', 'Yellow'][cam2_id]})", 
                   (10, 30), font, 0.7, (255, 255, 255), 2)
        cv2.putText(combined, "White lines = Epipolar lines", (10, 60), font, 0.5, (255, 255, 255), 1)
        cv2.putText(combined, "Perfect calibration = Features align on same lines", 
                   (10, 85), font, 0.5, (255, 255, 255), 1)
        
        return combined, rect1, rect2
    
    def capture_and_verify(self):
        """Capture frame and create verification images"""
        print("Capturing verification frame...")
        
        # Capture frame
        frame = self.camera.capture_array()
        cameras = self.split_camera_frame(frame)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {}
        
        # Process each stereo pair
        for pair_name, maps in self.rectification_maps.items():
            cam1_id, cam2_id = map(int, pair_name.split('-'))
            
            if cam1_id in cameras and cam2_id in cameras:
                print(f"Processing camera pair {cam1_id}-{cam2_id}...")
                
                verification_img, rect1, rect2 = self.create_alignment_verification(
                    cameras[cam1_id], cameras[cam2_id], cam1_id, cam2_id, pair_name
                )
                
                if verification_img is not None:
                    # Save verification image
                    verify_file = f"{self.output_dir}/alignment_verification_{cam1_id}_{cam2_id}_{timestamp}.png"
                    cv2.imwrite(verify_file, verification_img)
                    
                    # Save individual rectified images
                    rect1_file = f"{self.output_dir}/rectified_cam{cam1_id}_{timestamp}.png"
                    rect2_file = f"{self.output_dir}/rectified_cam{cam2_id}_{timestamp}.png"
                    cv2.imwrite(rect1_file, rect1)
                    cv2.imwrite(rect2_file, rect2)
                    
                    results[pair_name] = {
                        'verification': verify_file,
                        'rectified1': rect1_file,
                        'rectified2': rect2_file
                    }
                    
                    print(f"✓ Saved verification for cameras {cam1_id}-{cam2_id}")
        
        return results
    
    def create_master_overlay(self):
        """Create a master overlay showing all 4 cameras"""
        print("Creating master 4-camera overlay...")
        
        # Capture frame
        frame = self.camera.capture_array()
        cameras = self.split_camera_frame(frame)
        
        # For master overlay, we need to choose one rectification to apply to all
        # Let's use the 0-3 horizontal rectification as reference
        if "0-3" in self.rectification_maps:
            base_maps = self.rectification_maps["0-3"]
            
            # Apply same rectification parameters to all cameras (approximate)
            rectified_cameras = {}
            for cam_id, cam_img in cameras.items():
                if cam_id in [0, 3]:
                    # These have exact rectification
                    if cam_id == 0:
                        rectified = cv2.remap(cam_img, base_maps['map1_x'], base_maps['map1_y'], cv2.INTER_LINEAR)
                    else:  # cam_id == 3
                        rectified = cv2.remap(cam_img, base_maps['map2_x'], base_maps['map2_y'], cv2.INTER_LINEAR)
                else:
                    # For cameras 1,2 use approximate rectification
                    rectified = cam_img  # Could be improved with proper cross-pair rectification
                
                rectified_cameras[cam_id] = rectified
            
            # Create master overlay
            master_height, master_width = rectified_cameras[0].shape[:2]
            master_overlay = np.zeros((master_height, master_width, 3), dtype=np.uint8)
            
            # Blend all cameras
            for cam_id, rectified in rectified_cameras.items():
                color = self.camera_colors[cam_id]
                colored = self.create_colored_overlay(rectified, color, self.transparency)
                master_overlay = cv2.addWeighted(master_overlay, 1.0, colored, 0.25, 0)
            
            # Add grid lines
            h, w = master_overlay.shape[:2]
            for y in range(0, h, 20):
                cv2.line(master_overlay, (0, y), (w, y), (128, 128, 128), 1)
            for x in range(0, w, 40):
                cv2.line(master_overlay, (x, 0), (x, h), (128, 128, 128), 1)
            
            # Add legend
            legend_y = 20
            for cam_id, color in self.camera_colors.items():
                cv2.putText(master_overlay, f"Camera {cam_id}", (10, legend_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                legend_y += 25
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            master_file = f"{self.output_dir}/master_overlay_{timestamp}.png"
            cv2.imwrite(master_file, master_overlay)
            
            print(f"✓ Saved master overlay: {master_file}")
            return master_file
        
        return None
    
    def run_verification(self):
        """Run complete verification process"""
        print("=== Calibration Visual Verification ===")
        print("This will create colored overlays to verify calibration quality")
        print("Perfect calibration = perfect alignment in overlapping regions")
        print()
        
        if not self.rectification_maps:
            print("❌ No rectification maps found!")
            print("Please run calibration first using the web interface.")
            return
        
        # Generate verification images
        results = self.capture_and_verify()
        
        # Generate master overlay
        master_file = self.create_master_overlay()
        
        print("\n=== Verification Complete ===")
        print(f"📁 All images saved to: {self.output_dir}")
        print("\n📋 How to interpret results:")
        print("• White lines = Epipolar lines (should align across cameras)")
        print("• Colored overlays = Different cameras")
        print("• Perfect alignment = Features on same horizontal lines")
        print("• Misalignment = Calibration needs improvement")
        
        if results:
            print(f"\n✅ Generated {len(results)} stereo pair verifications")
            for pair_name in results:
                print(f"   • Camera pair {pair_name}")
        
        if master_file:
            print("✅ Generated master 4-camera overlay")
        
        print("\n🔍 Open the images to visually inspect calibration quality!")
    
    def stop(self):
        """Clean up camera resources"""
        if self.camera:
            self.camera.stop()

def main():
    print("Calibration Visual Verification Tool")
    print("====================================")
    
    try:
        verifier = CalibrationVisualVerifier()
        verifier.run_verification()
        
    except KeyboardInterrupt:
        print("\nStopping verification...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            verifier.stop()
        except:
            pass

if __name__ == "__main__":
    main() 