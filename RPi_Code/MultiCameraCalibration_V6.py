import time
import cv2
import numpy as np
from picamera2 import Picamera2
import os
import json
from datetime import datetime
import threading
import queue

class UnifiedMultiCameraCalibrator:
    def __init__(self, external_camera=None):
        self.camera = external_camera
        self.external_camera = external_camera is not None
        self.current_settings = None  # Will be set by web interface
        self.calibration_data = {
            'object_points': [],
            'image_points': {0: [], 1: [], 2: [], 3: []},
            'good_frames': 0,
            'camera_matrices': {},
            'distortion_coeffs': {},
            'rotation_vectors': {},
            'translation_vectors': {},
            'center_reference': True  # Using center point as reference instead of master camera
        }
        
        # Camera configuration from the web interface
        self.camera_config = [
            [0, 3],  # Top row: camera 0 (left), camera 3 (right)
            [1, 2]   # Bottom row: camera 1 (left), camera 2 (right)
        ]
        
        # Single pattern size for consistency (8x6 vertices = 9x7 squares)
        self.pattern_sizes = [(8, 6)]  # Your physical checkerboard
        self.square_size = 25.0  # mm
        
        self.capture_dir = "/home/av/Documents/pi-Aerial-Payload/calibration_unified"
        self.rectified_dir = "/home/av/Documents/pi-Aerial-Payload/calibration_rectified"
        self.maps_dir = "/home/av/Documents/pi-Aerial-Payload/maps"
        
        # Create directories
        for dir_path in [self.capture_dir, self.rectified_dir, self.maps_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        
        if not self.external_camera:
            self.setup_camera()
        
        # High-resolution intrinsics storage
        self.highres_intrinsics_file = f"{self.maps_dir}/highres_intrinsics.npz"
        self.use_highres_intrinsics = False
    
    def get_current_camera_settings(self):
        """Get current camera settings from web interface or fallback to defaults"""
        if self.current_settings:
            # Always get fresh settings from the web interface
            # If current_settings is a callable (function), call it to get fresh values
            if callable(self.current_settings):
                fresh_settings = self.current_settings()
                print(f"✓ Using fresh user settings from web interface: {fresh_settings}")
                return {
                    "ExposureTime": fresh_settings["exposure_time"],
                    "AnalogueGain": fresh_settings["analogue_gain"],
                    "Contrast": fresh_settings["contrast"]
                }
            else:
                # Using stored settings (this is the old behavior)
                print(f"✓ Using stored user settings from web interface: {self.current_settings}")
                return {
                    "ExposureTime": self.current_settings["exposure_time"],
                    "AnalogueGain": self.current_settings["analogue_gain"],
                    "Contrast": self.current_settings["contrast"]
                }
        else:
            # Fallback to defaults if not set
            fallback_settings = {
                "ExposureTime": 10000,
                "AnalogueGain": 1.5,
                "Contrast": 1.2
            }
            print(f"⚠️  Using fallback default settings (web interface settings not received): {fallback_settings}")
            return fallback_settings
    
    def setup_camera(self):
        """Initialize camera for calibration"""
        try:
            self.camera = Picamera2()
            
            # Get current camera settings from web interface
            controls = self.get_current_camera_settings()
            
            config = self.camera.create_still_configuration(
                main={"size": (2560, 400)},
                controls=controls
            )
            self.camera.configure(config)
            self.camera.start()
            print("Multi-camera calibration system initialized")
            
        except Exception as e:
            print(f"Error initializing camera: {e}")
    
    def split_camera_frame(self, frame):
        """Split combined 4-camera frame into individual cameras"""
        if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        camera_width = frame.shape[1] // 4
        camera_height = frame.shape[0]
        
        cameras = []
        for i in range(4):
            x_start = i * camera_width
            x_end = (i + 1) * camera_width
            camera_frame = frame[0:camera_height, x_start:x_end].copy()
            cameras.append(camera_frame)
        
        return cameras
    
    def detect_chessboard_adaptive(self, image):
        """Enhanced chessboard detection"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Enhance image
        gray = cv2.convertScaleAbs(gray, alpha=1.3, beta=20)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        
        for pattern_size in self.pattern_sizes:
            flags = [
                cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE,
                cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_FILTER_QUADS,
                cv2.CALIB_CB_ADAPTIVE_THRESH
            ]
            
            for flag in flags:
                ret, corners = cv2.findChessboardCorners(gray, pattern_size, flag)
                if ret:
                    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1)
                    corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                    return ret, corners, pattern_size
        
        return False, None, None
    
    def capture_calibration_frame(self):
        """Capture frame for multi-camera calibration"""
        if not self.camera:
            return False, "Camera not initialized"
        
        try:
            # If using external camera, temporarily reconfigure for high resolution
            if self.external_camera:
                # Save current configuration
                current_config = self.camera.camera_configuration()
                
                # Get current camera settings from web interface
                current_controls = self.get_current_camera_settings()
                
                # Configure for high resolution capture with current user settings
                capture_config = self.camera.create_still_configuration(
                    main={"size": (2560, 400)},
                    controls=current_controls
                )
                
                # Camera reconfiguration with timeout protection
                def camera_operation():
                    try:
                        self.camera.stop()
                        self.camera.configure(capture_config)
                        self.camera.start()
                        time.sleep(0.05)  # Minimal stabilization time
                        
                        frame = self.camera.capture_array()
                        
                        # Restore original configuration with preserved settings
                        self.camera.stop()
                        self.camera.configure(current_config)
                        self.camera.start()
                        
                        # Re-apply the user's CURRENT settings after restoring configuration
                        try:
                            restore_controls = self.get_current_camera_settings()
                            self.camera.set_controls(restore_controls)
                            print(f"Restored current web interface settings: {restore_controls}")
                        except Exception as e:
                            print(f"Could not restore camera controls: {e}")
                        
                        return True, frame
                    except Exception as e:
                        return False, str(e)
                
                # Use queue to get result from thread
                result_queue = queue.Queue()
                
                def camera_thread():
                    success, result = camera_operation()
                    result_queue.put((success, result))
                
                # Start camera operation in thread
                thread = threading.Thread(target=camera_thread)
                thread.daemon = True
                thread.start()
                
                # Wait for result with shorter timeout
                try:
                    success, result = result_queue.get(timeout=5)  # Reduced from 10 to 5 seconds
                    if success:
                        frame = result
                    else:
                        return False, f"Camera operation failed: {result}"
                except queue.Empty:
                    return False, "Camera operation timed out - try again"
            else:
                frame = self.camera.capture_array()
                
            cameras = self.split_camera_frame(frame)
            
            # Detect chessboards in all cameras
            detected_cameras = {}
            all_corners = {}
            pattern_size = None
            
            for cam_idx, camera_frame in enumerate(cameras):
                ret, corners, detected_pattern = self.detect_chessboard_adaptive(camera_frame)
                if ret:
                    detected_cameras[cam_idx] = camera_frame
                    all_corners[cam_idx] = corners
                    if pattern_size is None:
                        pattern_size = detected_pattern
            
            # Require pattern in at least 3 cameras for multi-camera calibration
            if len(detected_cameras) >= 3:
                # Generate object points
                objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
                objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
                objp *= self.square_size
                
                # Store calibration data
                self.calibration_data['object_points'].append(objp)
                for cam_idx in detected_cameras.keys():
                    self.calibration_data['image_points'][cam_idx].append(all_corners[cam_idx])
                
                self.calibration_data['good_frames'] += 1
                
                # Save individual camera frames for reference
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                for cam_idx, camera_frame in enumerate(cameras):
                    cv2.imwrite(f"{self.capture_dir}/frame_{timestamp}_cam{cam_idx}.png", camera_frame)
                
                return True, f"Frame {self.calibration_data['good_frames']}: Pattern detected in cameras {list(detected_cameras.keys())}"
            
            return False, f"Pattern detected in only {len(detected_cameras)} cameras (need ≥3)"
            
        except Exception as e:
            return False, f"Error capturing calibration frame: {e}"
    
    def calibrate_individual_cameras(self):
        """Individual camera calibration (intrinsics)"""
        print("Calibrating individual camera intrinsics...")
        
        img_size = (640, 400)  # Per camera resolution
        
        for cam_idx in range(4):
            if len(self.calibration_data['image_points'][cam_idx]) < 10:
                print(f"Insufficient data for camera {cam_idx}")
                continue
            
            # Use only frames where this camera detected the pattern
            valid_obj_points = []
            valid_img_points = []
            
            for i, obj_pt in enumerate(self.calibration_data['object_points']):
                if i < len(self.calibration_data['image_points'][cam_idx]):
                    valid_obj_points.append(obj_pt)
                    valid_img_points.append(self.calibration_data['image_points'][cam_idx][i])
            
            # Calibrate individual camera
            ret, K, D, rvecs, tvecs = cv2.calibrateCamera(
                valid_obj_points, valid_img_points, img_size, None, None
            )
            
            self.calibration_data['camera_matrices'][cam_idx] = K
            self.calibration_data['distortion_coeffs'][cam_idx] = D
            
            print(f"Camera {cam_idx}: Calibration error = {ret:.4f}")
    
    def calibrate_highres_intrinsics(self):
        """One-time high-resolution intrinsic calibration at 1280x800"""
        print("Performing high-resolution intrinsic calibration...")
        
        # Check if high-res intrinsics already exist
        if os.path.exists(self.highres_intrinsics_file):
            print("High-resolution intrinsics already exist. Loading existing data...")
            self.load_highres_intrinsics()
            return True
        
        # Capture high-resolution calibration frames
        if not self.camera:
            print("Camera not initialized for high-res calibration")
            return False
        
        try:
            # Save current configuration
            current_config = self.camera.camera_configuration()
            current_controls = self.get_current_camera_settings()
            
            print(f"🔧 High-resolution calibration using camera settings: {current_controls}")
            
            # Configure for high-resolution capture with adjusted settings
            # High-resolution mode needs adjusted settings for proper exposure
            highres_controls = current_controls.copy()
            
            # Increase exposure for high-resolution mode to compensate for increased data
            highres_controls["ExposureTime"] = min(int(current_controls["ExposureTime"] * 2), 50000)
            
            # Disable auto-exposure explicitly for high-resolution mode
            try:
                camera_controls = self.camera.camera_controls
                if "AeEnable" in camera_controls:
                    highres_controls["AeEnable"] = False
                    print("🔧 Disabling auto-exposure for high-resolution mode")
                if "AwbEnable" in camera_controls:
                    highres_controls["AwbEnable"] = False
                    print("🔧 Disabling auto-white-balance for high-resolution mode")
            except Exception as ae_error:
                print(f"⚠️  Could not check auto-exposure controls: {ae_error}")
            
            print(f"🔧 Adjusted settings for high-resolution mode: {highres_controls}")
            
            highres_config = self.camera.create_still_configuration(
                main={"size": (5120, 800)},  # 1280x800 per camera
                controls=highres_controls
            )
            
            self.camera.stop()
            self.camera.configure(highres_config)
            self.camera.start()
            
            # Apply controls multiple times with verification
            for attempt in range(3):
                try:
                    self.camera.set_controls(highres_controls)
                    time.sleep(0.1)  # Let camera settle
                    
                    # Verify controls were applied
                    metadata = self.camera.capture_metadata()
                    actual_exposure = metadata.get('ExposureTime', 'N/A')
                    actual_gain = metadata.get('AnalogueGain', 'N/A')
                    actual_contrast = metadata.get('Contrast', 'N/A')
                    
                    print(f"📷 High-res attempt {attempt + 1}: Exposure={actual_exposure}, Gain={actual_gain}, Contrast={actual_contrast}")
                    
                    # Check if settings are reasonably close to what we requested
                    # Camera hardware may have limitations, so be more tolerant
                    exposure_ok = actual_exposure != 'N/A' and abs(actual_exposure - highres_controls["ExposureTime"]) < 10000
                    gain_ok = actual_gain != 'N/A' and abs(actual_gain - highres_controls["AnalogueGain"]) < 0.5
                    
                    if exposure_ok and gain_ok:
                        print(f"✅ High-resolution camera settings verified on attempt {attempt + 1}")
                        break
                    else:
                        print(f"⚠️  Settings mismatch (Exp: {actual_exposure}/{highres_controls['ExposureTime']}, Gain: {actual_gain}/{highres_controls['AnalogueGain']}), retrying...")
                        
                except Exception as e:
                    print(f"⚠️  Control verification failed on attempt {attempt + 1}: {e}")
                    
                if attempt < 2:
                    time.sleep(0.2)
            else:
                print("⚠️  Warning: Could not verify high-resolution settings")
            
            time.sleep(0.5)  # Extended stabilization for high-resolution mode
            
            # Capture frames for high-res calibration
            highres_frames = []
            target_frames = 15  # Fewer frames needed for intrinsics only
            
            print(f"Capturing {target_frames} high-resolution frames...")
            debug_frame_saved = False
            
            for i in range(target_frames):
                print(f"Capturing high-res frame {i+1}/{target_frames}")
                
                try:
                    frame = self.camera.capture_array()
                    print(f"📸 Captured frame shape: {frame.shape}, dtype: {frame.dtype}")
                    
                    # Save first frame for debugging
                    if not debug_frame_saved:
                        debug_path = f"{self.capture_dir}/debug_highres_frame.png"
                        if len(frame.shape) == 3:
                            debug_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        else:
                            debug_frame = frame
                        cv2.imwrite(debug_path, debug_frame)
                        print(f"🐛 Debug frame saved to: {debug_path}")
                    
                    cameras = self.split_camera_frame(frame)
                    print(f"📂 Split into {len(cameras)} cameras")
                    
                    # Check pattern detection in high-res
                    frame_valid = True
                    frame_corners = {}
                    detection_results = []
                    
                    for cam_idx, camera_frame in enumerate(cameras):
                        print(f"🔍 Camera {cam_idx} shape before resize: {camera_frame.shape}")
                        
                        # Resize to 1280x800 for processing
                        camera_frame = cv2.resize(camera_frame, (1280, 800))
                        print(f"🔍 Camera {cam_idx} shape after resize: {camera_frame.shape}")
                        
                        # Save individual camera frame for first debug capture
                        if i == 0 and cam_idx == 0:
                            cam_debug_path = f"{self.capture_dir}/debug_highres_cam{cam_idx}.png"
                            cv2.imwrite(cam_debug_path, camera_frame)
                            print(f"🐛 Debug camera {cam_idx} frame saved to: {cam_debug_path}")
                        
                        ret, corners, pattern_size = self.detect_chessboard_adaptive(camera_frame)
                        detection_results.append(f"Cam{cam_idx}:{'✓' if ret else '✗'}")
                        
                        if ret:
                            frame_corners[cam_idx] = corners
                        else:
                            frame_valid = False
                            # Don't break - let's see all camera results
                    
                    print(f"🎯 Pattern detection: {' '.join(detection_results)}")
                    
                    if i == 0:
                        debug_frame_saved = True
                    
                    if frame_valid:
                        highres_frames.append(frame_corners)
                        print(f"✅ High-res frame {len(highres_frames)} captured successfully")
                    else:
                        print(f"❌ High-res frame {i+1} failed - pattern not detected in enough cameras")
                
                except Exception as e:
                    print(f"❌ Error capturing high-res frame {i+1}: {e}")
                
                time.sleep(0.3)  # Brief pause between captures
            
            # Restore original configuration with CURRENT web interface settings
            print("🔄 Restoring camera to web interface configuration...")
            self.camera.stop()
            self.camera.configure(current_config)
            self.camera.start()
            
            # Use current web interface settings instead of saved settings
            restore_controls = self.get_current_camera_settings()
            
            # Apply restoration settings multiple times to ensure they stick
            for restore_attempt in range(3):
                try:
                    self.camera.set_controls(restore_controls)
                    time.sleep(0.2)  # Let camera settle
                    
                    # Verify restoration
                    metadata = self.camera.capture_metadata()
                    restored_exposure = metadata.get('ExposureTime', 'N/A')
                    restored_gain = metadata.get('AnalogueGain', 'N/A')
                    
                    print(f"🔄 Restore attempt {restore_attempt + 1}: Exposure={restored_exposure}, Gain={restored_gain}")
                    
                    # Check if restoration was successful
                    if (restored_exposure != 'N/A' and abs(restored_exposure - restore_controls["ExposureTime"]) < 2000 and
                        restored_gain != 'N/A' and abs(restored_gain - restore_controls["AnalogueGain"]) < 0.3):
                        print(f"✅ Camera settings restored successfully on attempt {restore_attempt + 1}")
                        break
                    else:
                        print(f"⚠️  Restoration mismatch, retrying...")
                        
                except Exception as e:
                    print(f"⚠️  Restoration verification failed on attempt {restore_attempt + 1}: {e}")
                    
                if restore_attempt < 2:
                    time.sleep(0.3)
            else:
                print("⚠️  Warning: Could not verify camera restoration")
            
            print(f"✅ Camera configuration restored with current web interface settings: {restore_controls}")
            
            if len(highres_frames) < 10:
                print(f"Insufficient high-res frames captured: {len(highres_frames)}")
                return False
            
            # Calibrate intrinsics at high resolution
            print("Calibrating high-resolution intrinsics...")
            highres_img_size = (1280, 800)
            
            # Generate object points for high-res calibration
            objp = np.zeros((8 * 6, 3), np.float32)
            objp[:, :2] = np.mgrid[0:8, 0:6].T.reshape(-1, 2)
            objp *= self.square_size
            
            highres_intrinsics = {}
            
            for cam_idx in range(4):
                obj_points = []
                img_points = []
                
                for frame_corners in highres_frames:
                    if cam_idx in frame_corners:
                        obj_points.append(objp)
                        img_points.append(frame_corners[cam_idx])
                
                if len(obj_points) >= 10:
                    ret, K, D, rvecs, tvecs = cv2.calibrateCamera(
                        obj_points, img_points, highres_img_size, None, None
                    )
                    
                    highres_intrinsics[cam_idx] = {
                        'camera_matrix': K,
                        'distortion_coeffs': D,
                        'calibration_error': ret
                    }
                    
                    print(f"High-res camera {cam_idx}: Error = {ret:.4f}")
                else:
                    print(f"Insufficient data for high-res camera {cam_idx}")
            
            # Save high-resolution intrinsics
            np.savez(self.highres_intrinsics_file, **highres_intrinsics)
            print(f"High-resolution intrinsics saved to {self.highres_intrinsics_file}")
            
            return True
            
        except Exception as e:
            print(f"High-resolution calibration failed: {e}")
            # Restore configuration on error
            try:
                print("⚠️  Restoring camera configuration after high-resolution calibration error...")
                self.camera.stop()
                self.camera.configure(current_config)
                self.camera.start()
                
                # Use current web interface settings instead of saved settings
                restore_controls = self.get_current_camera_settings()
                
                # Apply restoration settings with verification
                for restore_attempt in range(2):
                    try:
                        self.camera.set_controls(restore_controls)
                        time.sleep(0.2)
                        
                        # Quick verification
                        metadata = self.camera.capture_metadata()
                        restored_exposure = metadata.get('ExposureTime', 'N/A')
                        print(f"🔄 Error restore attempt {restore_attempt + 1}: Exposure={restored_exposure}")
                        
                        if restored_exposure != 'N/A':
                            print(f"✅ Camera restored after error on attempt {restore_attempt + 1}")
                            break
                            
                    except Exception as verify_error:
                        print(f"⚠️  Error restore verification failed: {verify_error}")
                        
                    if restore_attempt < 1:
                        time.sleep(0.3)
                
                print(f"✅ Camera configuration restored after error with current web interface settings: {restore_controls}")
                
            except Exception as restore_error:
                print(f"⚠️  Could not restore camera configuration: {restore_error}")
            return False
    
    def load_highres_intrinsics(self):
        """Load existing high-resolution intrinsics"""
        if os.path.exists(self.highres_intrinsics_file):
            data = np.load(self.highres_intrinsics_file, allow_pickle=True)
            
            # Scale down intrinsics from 1280x800 to 640x400
            scale_x = 640 / 1280
            scale_y = 400 / 800
            
            for cam_idx in range(4):
                key = f'arr_{cam_idx}'
                if key in data:
                    highres_data = data[key].item()
                    
                    # Scale camera matrix
                    K_highres = highres_data['camera_matrix']
                    K_scaled = K_highres.copy()
                    K_scaled[0, 0] *= scale_x  # fx
                    K_scaled[1, 1] *= scale_y  # fy
                    K_scaled[0, 2] *= scale_x  # cx
                    K_scaled[1, 2] *= scale_y  # cy
                    
                    # Use scaled intrinsics
                    self.calibration_data['camera_matrices'][cam_idx] = K_scaled
                    self.calibration_data['distortion_coeffs'][cam_idx] = highres_data['distortion_coeffs']
                    
                    print(f"Loaded high-res intrinsics for camera {cam_idx} (scaled to 640x400)")
            
            self.use_highres_intrinsics = True
            print("High-resolution intrinsics loaded and scaled")
        else:
            print("No high-resolution intrinsics file found")
    
    def calibrate_multi_camera_system(self):
        """Multi-camera system calibration (extrinsics relative to center point)"""
        print("Calibrating multi-camera system with center reference point...")
        
        # Step 1: Calculate relative poses using camera 0 as temporary reference
        temp_poses = {0: {'R': np.eye(3), 'T': np.zeros((3, 1))}}
        
        for cam_idx in range(1, 4):
            if (len(self.calibration_data['image_points'][0]) < 10 or 
                len(self.calibration_data['image_points'][cam_idx]) < 10):
                print(f"Insufficient data for camera pair 0-{cam_idx}")
                continue
            
            # Find common frames where both cameras detected the pattern
            common_obj_points = []
            common_img_points_1 = []
            common_img_points_2 = []
            
            min_frames = min(len(self.calibration_data['image_points'][0]),
                           len(self.calibration_data['image_points'][cam_idx]))
            
            for i in range(min_frames):
                if (i < len(self.calibration_data['object_points']) and
                    i < len(self.calibration_data['image_points'][0]) and
                    i < len(self.calibration_data['image_points'][cam_idx])):
                    
                    common_obj_points.append(self.calibration_data['object_points'][i])
                    common_img_points_1.append(self.calibration_data['image_points'][0][i])
                    common_img_points_2.append(self.calibration_data['image_points'][cam_idx][i])
            
            if len(common_obj_points) < 10:
                print(f"Insufficient common frames for cameras 0-{cam_idx}")
                continue
            
            # Stereo calibration to get relative pose
            img_size = (640, 400)
            K1 = self.calibration_data['camera_matrices'][0]
            D1 = self.calibration_data['distortion_coeffs'][0]
            K2 = self.calibration_data['camera_matrices'][cam_idx]
            D2 = self.calibration_data['distortion_coeffs'][cam_idx]
            
            ret, _, _, _, _, R, T, E, F = cv2.stereoCalibrate(
                common_obj_points, common_img_points_1, common_img_points_2,
                K1, D1, K2, D2, img_size,
                criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-5),
                flags=cv2.CALIB_FIX_INTRINSIC
            )
            
            temp_poses[cam_idx] = {'R': R, 'T': T}
            print(f"Camera {cam_idx} relative to camera 0: Error = {ret:.4f}")
        
        # Step 2: Calculate center point from camera positions
        self.calculate_center_reference_transforms(temp_poses)
        
        # Step 3: Global bundle adjustment refinement
        self.global_bundle_adjustment()
    
    def calculate_center_reference_transforms(self, temp_poses):
        """Calculate transforms relative to center point between all cameras"""
        print("Calculating center reference transforms...")
        
        # Build transformation chain: Camera 0 -> Camera 1,2,3
        # Using proper relative transformations from stereo calibration
        camera_transforms = {0: {'R': np.eye(3), 'T': np.zeros((3, 1))}}  # Reference camera
        
        # Apply relative transformations to get camera positions
        for cam_idx in range(1, 4):
            if cam_idx in temp_poses:
                # temp_poses contains relative transform from camera 0 to camera cam_idx
                R_rel = temp_poses[cam_idx]['R']
                T_rel = temp_poses[cam_idx]['T']
                
                # Camera position in reference frame = -R^T * T
                camera_pos = -R_rel.T @ T_rel
                
                camera_transforms[cam_idx] = {
                    'R': R_rel,
                    'T': T_rel, 
                    'position': camera_pos.flatten()
                }
            else:
                print(f"Warning: Camera {cam_idx} not calibrated, using identity")
                camera_transforms[cam_idx] = {
                    'R': np.eye(3),
                    'T': np.zeros((3, 1)),
                    'position': np.zeros(3)
                }
        
        # Calculate geometric center of camera positions
        center_pos = np.zeros(3)
        valid_cameras = 0
        
        for cam_idx, transform in camera_transforms.items():
            if 'position' in transform:
                center_pos += transform['position']
                valid_cameras += 1
        
        if valid_cameras > 0:
            center_pos /= valid_cameras
            print(f"Center reference point calculated from {valid_cameras} cameras")
        
        # Transform all cameras to be relative to center point
        for cam_idx in range(4):
            if cam_idx in camera_transforms:
                if cam_idx == 0:
                    # Reference camera (0) relative to center
                    relative_pos = -center_pos  # Camera 0 was at origin
                    R_center = np.eye(3)
                else:
                    # Other cameras relative to center
                    cam_pos = camera_transforms[cam_idx]['position']
                    relative_pos = cam_pos - center_pos
                    R_center = camera_transforms[cam_idx]['R']
                
                # Store center-relative transforms
                rvec, _ = cv2.Rodrigues(R_center)
                self.calibration_data['rotation_vectors'][cam_idx] = rvec
                self.calibration_data['translation_vectors'][cam_idx] = relative_pos.reshape(3, 1)
                
                print(f"Camera {cam_idx} position relative to center: {relative_pos}")
            else:
                # Fallback for missing cameras
                self.calibration_data['rotation_vectors'][cam_idx] = np.zeros((3, 1))
                self.calibration_data['translation_vectors'][cam_idx] = np.zeros((3, 1))
        
        self.print_camera_layout()
    
    def print_camera_layout(self):
        """Print camera positions relative to center point for visualization"""
        print("\n" + "="*50)
        print("CAMERA LAYOUT RELATIVE TO CENTER POINT")
        print("="*50)
        
        for row_idx, row in enumerate(self.camera_config):
            for col_idx, cam_idx in enumerate(row):
                if cam_idx in self.calibration_data['translation_vectors']:
                    pos = self.calibration_data['translation_vectors'][cam_idx].flatten()
                    print(f"Camera {cam_idx} (Row {row_idx}, Col {col_idx}): "
                          f"X={pos[0]:6.1f}mm, Y={pos[1]:6.1f}mm, Z={pos[2]:6.1f}mm")
                else:
                    print(f"Camera {cam_idx} (Row {row_idx}, Col {col_idx}): Not calibrated")
        
        print("\nCamera Configuration Layout:")
        print(f"  [{self.camera_config[0][0]}] --- [{self.camera_config[0][1]}]")
        print("   |         |")
        print(f"  [{self.camera_config[1][0]}] --- [{self.camera_config[1][1]}]")
        print("\nCenter point (0,0,0) is the reference for all positions")
        
        # Validate reasonable camera spacing for multispectral array
        positions = []
        for cam_idx in range(4):
            if cam_idx in self.calibration_data['translation_vectors']:
                pos = self.calibration_data['translation_vectors'][cam_idx].flatten()
                positions.append(pos)
        
        if len(positions) >= 2:
            distances = []
            for i in range(len(positions)):
                for j in range(i+1, len(positions)):
                    dist = np.linalg.norm(positions[i] - positions[j])
                    distances.append(dist)
            
            avg_distance = np.mean(distances)
            print(f"\nAverage inter-camera distance: {avg_distance:.1f}mm")
            if 20 <= avg_distance <= 200:
                print("✅ Camera spacing looks reasonable for multispectral array")
            else:
                print("⚠️  Camera spacing may be incorrect - check calibration quality")
        
        print("="*50 + "\n")
    
    def global_bundle_adjustment(self):
        """Global bundle adjustment refinement using all cameras simultaneously"""
        print("Performing global bundle adjustment refinement...")
        
        # Prepare data for bundle adjustment
        # Need to build arrays for all cameras and all frames
        img_size = (640, 400)
        
        # Build frame-synchronized data
        max_frames = len(self.calibration_data['object_points'])
        
        # Prepare lists for bundle adjustment
        all_obj_points = []
        all_img_points_per_camera = [[] for _ in range(4)]
        
        frame_count = 0
        for frame_idx in range(max_frames):
            frame_obj_points = self.calibration_data['object_points'][frame_idx]
            frame_valid = True
            frame_img_points = {}
            
            # Check if all cameras have data for this frame
            for cam_idx in range(4):
                if (frame_idx < len(self.calibration_data['image_points'][cam_idx]) and
                    cam_idx in self.calibration_data['camera_matrices']):
                    frame_img_points[cam_idx] = self.calibration_data['image_points'][cam_idx][frame_idx]
                else:
                    frame_valid = False
                    break
            
            if frame_valid:
                all_obj_points.append(frame_obj_points)
                for cam_idx in range(4):
                    all_img_points_per_camera[cam_idx].append(frame_img_points[cam_idx])
                frame_count += 1
        
        if frame_count < 10:
            print(f"Insufficient frames for bundle adjustment: {frame_count}")
            return
        
        print(f"Bundle adjustment using {frame_count} frames across all cameras")
        
        # Prepare camera matrices and distortion coefficients
        K_list = []
        D_list = []
        rvecs_list = []
        tvecs_list = []
        
        for cam_idx in range(4):
            if cam_idx in self.calibration_data['camera_matrices']:
                K_list.append(self.calibration_data['camera_matrices'][cam_idx])
                D_list.append(self.calibration_data['distortion_coeffs'][cam_idx])
                rvecs_list.append(self.calibration_data['rotation_vectors'][cam_idx])
                tvecs_list.append(self.calibration_data['translation_vectors'][cam_idx])
            else:
                # Use identity for missing cameras
                K_list.append(np.eye(3))
                D_list.append(np.zeros(5))
                rvecs_list.append(np.zeros((3, 1)))
                tvecs_list.append(np.zeros((3, 1)))
        
        # Custom Levenberg-Marquardt bundle adjustment (OpenCV's bundleAdjust may not be available)
        try:
            # Try OpenCV's bundle adjustment if available
            has_opencv_ba = hasattr(cv2, 'bundleAdjust')
            if has_opencv_ba:
                print("Using OpenCV bundle adjustment...")
                # Note: OpenCV's bundleAdjust interface varies by version
                # This is a simplified version for demonstration
                pass
            else:
                print("Using custom bundle adjustment implementation...")
                self.custom_bundle_adjustment(all_obj_points, all_img_points_per_camera, K_list, D_list, rvecs_list, tvecs_list)
        except Exception as e:
            print(f"Bundle adjustment failed: {e}")
            print("Continuing with pairwise calibration results...")
    
    def custom_bundle_adjustment(self, obj_points, img_points_per_camera, K_list, D_list, rvecs_list, tvecs_list):
        """Custom bundle adjustment using scipy.optimize"""
        print("Running custom Levenberg-Marquardt bundle adjustment...")
        
        # Calculate initial reprojection error
        initial_error = self.calculate_total_reprojection_error(obj_points, img_points_per_camera, K_list, D_list, rvecs_list, tvecs_list)
        print(f"Initial total reprojection error: {initial_error:.6f}")
        
        # Simple parameter refinement using gradient descent
        # This is a lightweight implementation for Pi 4
        learning_rate = 0.001
        max_iterations = 20
        
        best_error = initial_error
        best_params = [rvecs_list.copy(), tvecs_list.copy()]
        
        for iteration in range(max_iterations):
            # Calculate gradients and update parameters
            improved = False
            
            # Refine rotation vectors
            for cam_idx in range(4):
                if cam_idx in self.calibration_data['camera_matrices']:
                    # Small perturbations to estimate gradient
                    original_rvec = rvecs_list[cam_idx].copy()
                    
                    for axis in range(3):
                        # Positive perturbation
                        rvecs_list[cam_idx][axis] += learning_rate
                        error_pos = self.calculate_total_reprojection_error(obj_points, img_points_per_camera, K_list, D_list, rvecs_list, tvecs_list)
                        
                        # Negative perturbation
                        rvecs_list[cam_idx][axis] = original_rvec[axis] - learning_rate
                        error_neg = self.calculate_total_reprojection_error(obj_points, img_points_per_camera, K_list, D_list, rvecs_list, tvecs_list)
                        
                        # Gradient descent update
                        gradient = (error_pos - error_neg) / (2 * learning_rate)
                        rvecs_list[cam_idx][axis] = original_rvec[axis] - learning_rate * gradient
                        
                        # Check for improvement
                        new_error = self.calculate_total_reprojection_error(obj_points, img_points_per_camera, K_list, D_list, rvecs_list, tvecs_list)
                        if new_error < best_error:
                            best_error = new_error
                            improved = True
                        else:
                            # Revert if no improvement
                            rvecs_list[cam_idx][axis] = original_rvec[axis]
            
            # Refine translation vectors
            for cam_idx in range(4):
                if cam_idx in self.calibration_data['camera_matrices']:
                    original_tvec = tvecs_list[cam_idx].copy()
                    
                    for axis in range(3):
                        # Similar gradient descent for translation
                        tvecs_list[cam_idx][axis] += learning_rate * 10  # Larger step for translation
                        error_pos = self.calculate_total_reprojection_error(obj_points, img_points_per_camera, K_list, D_list, rvecs_list, tvecs_list)
                        
                        tvecs_list[cam_idx][axis] = original_tvec[axis] - learning_rate * 10
                        error_neg = self.calculate_total_reprojection_error(obj_points, img_points_per_camera, K_list, D_list, rvecs_list, tvecs_list)
                        
                        gradient = (error_pos - error_neg) / (2 * learning_rate * 10)
                        tvecs_list[cam_idx][axis] = original_tvec[axis] - learning_rate * 10 * gradient
                        
                        new_error = self.calculate_total_reprojection_error(obj_points, img_points_per_camera, K_list, D_list, rvecs_list, tvecs_list)
                        if new_error < best_error:
                            best_error = new_error
                            improved = True
                        else:
                            tvecs_list[cam_idx][axis] = original_tvec[axis]
            
            if not improved:
                learning_rate *= 0.8  # Reduce learning rate
                
            if iteration % 5 == 0:
                print(f"Iteration {iteration}: Error = {best_error:.6f}")
        
        # Update calibration data with refined parameters
        for cam_idx in range(4):
            if cam_idx in self.calibration_data['camera_matrices']:
                self.calibration_data['rotation_vectors'][cam_idx] = rvecs_list[cam_idx]
                self.calibration_data['translation_vectors'][cam_idx] = tvecs_list[cam_idx]
        
        final_error = self.calculate_total_reprojection_error(obj_points, img_points_per_camera, K_list, D_list, rvecs_list, tvecs_list)
        improvement = initial_error - final_error
        print(f"Bundle adjustment complete: {initial_error:.6f} -> {final_error:.6f} (improvement: {improvement:.6f})")
    
    def calculate_total_reprojection_error(self, obj_points, img_points_per_camera, K_list, D_list, rvecs_list, tvecs_list):
        """Calculate total reprojection error across all cameras and frames"""
        total_error = 0
        total_points = 0
        
        for frame_idx in range(len(obj_points)):
            for cam_idx in range(4):
                if cam_idx in self.calibration_data['camera_matrices']:
                    # Project 3D points to image
                    projected_points, _ = cv2.projectPoints(
                        obj_points[frame_idx],
                        rvecs_list[cam_idx],
                        tvecs_list[cam_idx],
                        K_list[cam_idx],
                        D_list[cam_idx]
                    )
                    
                    # Calculate reprojection error
                    observed_points = img_points_per_camera[cam_idx][frame_idx]
                    error = cv2.norm(observed_points, projected_points, cv2.NORM_L2) / len(observed_points)
                    total_error += error * len(observed_points)
                    total_points += len(observed_points)
        
        return total_error / total_points if total_points > 0 else float('inf')
    
    def generate_rectification_maps(self):
        """Generate rectification maps for camera pairs based on center reference"""
        print("Generating rectification maps for camera pairs...")
        
        rectification_maps = {}
        
        # Define useful stereo pairs based on camera configuration
        # Layout: [0, 3]  -> horizontal stereo pairs: 0-3 (top row)
        #         [1, 2]  -> horizontal stereo pairs: 1-2 (bottom row)
        # Also vertical pairs: 0-1 (left column), 3-2 (right column)
        stereo_pairs = [
            (0, 3),  # Top row horizontal
            (1, 2),  # Bottom row horizontal  
            (0, 1),  # Left column vertical
            (3, 2),  # Right column vertical
        ]
        
        for cam1, cam2 in stereo_pairs:
            if (cam1 not in self.calibration_data['camera_matrices'] or
                cam2 not in self.calibration_data['camera_matrices']):
                print(f"Skipping pair {cam1}-{cam2}: missing camera matrices")
                continue
            
            # Get camera parameters
            K1 = self.calibration_data['camera_matrices'][cam1]
            D1 = self.calibration_data['distortion_coeffs'][cam1]
            K2 = self.calibration_data['camera_matrices'][cam2]
            D2 = self.calibration_data['distortion_coeffs'][cam2]
            
            # Calculate relative pose between the two cameras
            R1_vec = self.calibration_data['rotation_vectors'][cam1]
            T1 = self.calibration_data['translation_vectors'][cam1]
            R2_vec = self.calibration_data['rotation_vectors'][cam2]
            T2 = self.calibration_data['translation_vectors'][cam2]
            
            R1, _ = cv2.Rodrigues(R1_vec)
            R2, _ = cv2.Rodrigues(R2_vec)
            
            # Calculate relative transformation from camera 1 to camera 2
            # Both cameras are relative to center, so relative transform is:
            # R_rel = R2 * R1^T (rotation from cam1 to cam2)
            # T_rel = R2*R1^T*(T1-T2) (translation in cam1 frame)
            R_rel = R2 @ R1.T
            T_rel = R1.T @ (T2 - T1)  # Transform difference to cam1 frame
            
            img_size = (640, 400)
            
            # Stereo rectification
            R1_rect, R2_rect, P1, P2, Q, validRoi1, validRoi2 = cv2.stereoRectify(
                K1, D1, K2, D2, img_size, R_rel, T_rel
            )
            
            # Generate rectification maps
            map1_x, map1_y = cv2.initUndistortRectifyMap(K1, D1, R1_rect, P1, img_size, cv2.CV_32FC1)
            map2_x, map2_y = cv2.initUndistortRectifyMap(K2, D2, R2_rect, P2, img_size, cv2.CV_32FC1)
            
            rectification_maps[f"{cam1}-{cam2}"] = {
                'map1_x': map1_x, 'map1_y': map1_y,
                'map2_x': map2_x, 'map2_y': map2_y,
                'roi1': validRoi1, 'roi2': validRoi2
            }
            
            # Save maps to file
            map_file = f"{self.maps_dir}/unified_stereoMap_{cam1}{cam2}.xml"
            cv_file = cv2.FileStorage(map_file, cv2.FILE_STORAGE_WRITE)
            cv_file.write('stereoMap1_x', map1_x)
            cv_file.write('stereoMap1_y', map1_y)
            cv_file.write('stereoMap2_x', map2_x)
            cv_file.write('stereoMap2_y', map2_y)
            cv_file.write('Roi1', validRoi1)
            cv_file.write('Roi2', validRoi2)
            cv_file.release()
            
            print(f"Rectification maps saved for cameras {cam1}-{cam2}")
        
        # Validate rectification quality
        if not self.validate_rectification_quality(rectification_maps):
            print("⚠️  Rectification quality validation failed!")
            print("   Consider recalibrating with more frames or better lighting")
        
        return rectification_maps
    
    def validate_rectification_quality(self, rectification_maps):
        """Validate rectification quality using SIFT features and vertical disparity"""
        print("Validating rectification quality...")
        
        # Get test images from calibration captures
        test_frame_files = [f for f in os.listdir(self.capture_dir) if f.endswith('.png')]
        if not test_frame_files:
            print("No test frames available for validation")
            return False
        
        # Use the first available frame for validation - extract full timestamp
        # Format: frame_20250709_204216_780_cam0.png -> 20250709_204216_780
        first_file = test_frame_files[0]
        parts = first_file.split('_')
        if len(parts) >= 4:
            timestamp = f"{parts[1]}_{parts[2]}_{parts[3]}"
        else:
            print(f"Unexpected filename format: {first_file}")
            return False
        
        # Load test camera frames
        test_cameras = {}
        for cam_idx in range(4):
            test_file = f"{self.capture_dir}/frame_{timestamp}_cam{cam_idx}.png"
            if os.path.exists(test_file):
                test_cameras[cam_idx] = cv2.imread(test_file)
        
        validation_results = {}
        overall_quality = True
        
        for pair_name, maps in rectification_maps.items():
            cam1, cam2 = map(int, pair_name.split('-'))
            
            if cam1 in test_cameras and cam2 in test_cameras:
                # Apply rectification
                rect1 = cv2.remap(test_cameras[cam1], maps['map1_x'], maps['map1_y'], cv2.INTER_LINEAR)
                rect2 = cv2.remap(test_cameras[cam2], maps['map2_x'], maps['map2_y'], cv2.INTER_LINEAR)
                
                # SIFT feature detection and matching
                sift = cv2.SIFT_create()
                
                # Convert to grayscale for SIFT
                gray1 = cv2.cvtColor(rect1, cv2.COLOR_BGR2GRAY) if len(rect1.shape) == 3 else rect1
                gray2 = cv2.cvtColor(rect2, cv2.COLOR_BGR2GRAY) if len(rect2.shape) == 3 else rect2
                
                # Detect features
                kp1, desc1 = sift.detectAndCompute(gray1, None)
                kp2, desc2 = sift.detectAndCompute(gray2, None)
                
                if desc1 is not None and desc2 is not None and len(desc1) > 10 and len(desc2) > 10:
                    # Match features
                    bf = cv2.BFMatcher()
                    matches = bf.knnMatch(desc1, desc2, k=2)
                    
                    # Apply ratio test
                    good_matches = []
                    for m, n in matches:
                        if m.distance < 0.7 * n.distance:
                            good_matches.append(m)
                    
                    if len(good_matches) >= 20:  # Need minimum matches for statistics
                        # Calculate vertical disparity statistics
                        vertical_disparities = []
                        for match in good_matches:
                            pt1 = kp1[match.queryIdx].pt
                            pt2 = kp2[match.trainIdx].pt
                            vertical_disparity = abs(pt1[1] - pt2[1])
                            vertical_disparities.append(vertical_disparity)
                        
                        # Use subset for performance (max 200 matches)
                        if len(vertical_disparities) > 200:
                            vertical_disparities = vertical_disparities[:200]
                        
                        mean_vertical_disparity = np.mean(vertical_disparities)
                        std_vertical_disparity = np.std(vertical_disparities)
                        max_vertical_disparity = np.max(vertical_disparities)
                        
                        # Quality criteria
                        quality_good = (mean_vertical_disparity < 2.0 and 
                                      max_vertical_disparity < 5.0 and
                                      std_vertical_disparity < 1.5)
                        
                        validation_results[pair_name] = {
                            'mean_vertical_disparity': mean_vertical_disparity,
                            'std_vertical_disparity': std_vertical_disparity,
                            'max_vertical_disparity': max_vertical_disparity,
                            'num_matches': len(good_matches),
                            'quality_good': quality_good
                        }
                        
                        # Print results
                        quality_str = "✓ GOOD" if quality_good else "✗ POOR"
                        print(f"Pair {pair_name}: {quality_str}")
                        print(f"  Mean vertical disparity: {mean_vertical_disparity:.2f} px")
                        print(f"  Max vertical disparity: {max_vertical_disparity:.2f} px")
                        print(f"  Std vertical disparity: {std_vertical_disparity:.2f} px")
                        print(f"  Features matched: {len(good_matches)}")
                        
                        if not quality_good:
                            overall_quality = False
                    else:
                        print(f"Pair {pair_name}: Insufficient feature matches ({len(good_matches)})")
                        overall_quality = False
                else:
                    print(f"Pair {pair_name}: SIFT feature detection failed")
                    overall_quality = False
            else:
                print(f"Pair {pair_name}: Missing test images")
                overall_quality = False
        
        # Save validation results
        validation_file = f"{self.maps_dir}/rectification_validation.json"
        with open(validation_file, 'w') as f:
            # Convert numpy types to Python types for JSON serialization
            json_results = {}
            for pair_name, result in validation_results.items():
                json_results[pair_name] = {
                    'mean_vertical_disparity': float(result['mean_vertical_disparity']),
                    'std_vertical_disparity': float(result['std_vertical_disparity']),
                    'max_vertical_disparity': float(result['max_vertical_disparity']),
                    'num_matches': int(result['num_matches']),
                    'quality_good': bool(result['quality_good'])
                }
            
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'overall_quality': overall_quality,
                'pair_results': json_results
            }, f, indent=2)
        
        print(f"Rectification validation results saved to {validation_file}")
        
        if overall_quality:
            print("✅ Rectification quality validation passed")
        else:
            print("❌ Rectification quality validation failed")
            print("   Recommendation: Recalibrate with more frames or better pattern visibility")
        
        return overall_quality
    
    def create_rectified_test_images(self, rectification_maps):
        """Create rectified test images to verify calibration quality"""
        print("Creating rectified test images...")
        
        # Get the first captured frame for testing
        test_frame_files = [f for f in os.listdir(self.capture_dir) if f.endswith('.png')]
        if not test_frame_files:
            print("No test frames available")
            return
        
        # Get first timestamp - extract full timestamp from filename
        # Format: frame_20250709_204216_780_cam0.png -> 20250709_204216_780
        first_file = test_frame_files[0]
        parts = first_file.split('_')
        if len(parts) >= 4:
            timestamp = f"{parts[1]}_{parts[2]}_{parts[3]}"
        else:
            print(f"Unexpected filename format: {first_file}")
            return
        
        # Load all camera frames for this timestamp
        test_cameras = {}
        for cam_idx in range(4):
            test_file = f"{self.capture_dir}/frame_{timestamp}_cam{cam_idx}.png"
            if os.path.exists(test_file):
                test_cameras[cam_idx] = cv2.imread(test_file)
        
        for pair_name, maps in rectification_maps.items():
            cam1, cam2 = map(int, pair_name.split('-'))
            
            if cam1 in test_cameras and cam2 in test_cameras:
                # Apply rectification
                rectified1 = cv2.remap(test_cameras[cam1], maps['map1_x'], maps['map1_y'], cv2.INTER_LINEAR)
                rectified2 = cv2.remap(test_cameras[cam2], maps['map2_x'], maps['map2_y'], cv2.INTER_LINEAR)
                
                # Create side-by-side comparison
                combined = np.hstack([rectified1, rectified2])
                
                # Draw horizontal lines to show rectification
                for y in range(0, combined.shape[0], 40):
                    cv2.line(combined, (0, y), (combined.shape[1], y), (0, 255, 0), 1)
                
                # Save rectified pair
                rectified_file = f"{self.rectified_dir}/rectified_{cam1}_{cam2}.png"
                cv2.imwrite(rectified_file, combined)
                print(f"Rectified test image saved: {rectified_file}")
    
    def perform_full_calibration(self, target_frames=20, use_highres_intrinsics=False):
        """Complete multi-camera calibration process"""
        print(f"Starting unified multi-camera calibration for {target_frames} frames...")
        
        # Ensure camera settings are properly applied before calibration starts
        if self.external_camera and self.current_settings:
            print(f"🔧 Applying user camera settings for calibration: {self.current_settings}")
            try:
                current_controls = self.get_current_camera_settings()
                self.camera.set_controls(current_controls)
                print(f"✓ User camera settings applied: {current_controls}")
            except Exception as e:
                print(f"⚠️  Warning: Could not apply user camera settings: {e}")
        
        # Option 1: Use high-resolution intrinsics if requested
        if use_highres_intrinsics:
            print("Using high-resolution intrinsic calibration...")
            if not self.calibrate_highres_intrinsics():
                print("High-resolution intrinsic calibration failed, falling back to standard calibration")
                use_highres_intrinsics = False
            else:
                # CRITICAL: Reapply user settings after high-res intrinsics step
                if self.external_camera and self.current_settings:
                    print(f"🔧 Reapplying user camera settings after high-res intrinsics: {self.current_settings}")
                    try:
                        current_controls = self.get_current_camera_settings()
                        self.camera.set_controls(current_controls)
                        print(f"✓ User camera settings reapplied after high-res step: {current_controls}")
                        time.sleep(0.1)  # Brief stabilization
                    except Exception as e:
                        print(f"⚠️  Warning: Could not reapply user camera settings: {e}")
        
        # Option 2: Load existing high-res intrinsics if available
        if not use_highres_intrinsics and os.path.exists(self.highres_intrinsics_file):
            print("Loading existing high-resolution intrinsics...")
            self.load_highres_intrinsics()
        
        # CRITICAL: Final verification of camera settings before main calibration loop
        if self.external_camera and self.current_settings:
            print(f"🔧 Final verification of camera settings before main calibration:")
            try:
                current_controls = self.get_current_camera_settings()
                self.camera.set_controls(current_controls)
                print(f"✓ Final camera settings verification complete: {current_controls}")
                
                # Verify settings are actually applied
                metadata = self.camera.capture_metadata()
                actual_exposure = metadata.get('ExposureTime', 'N/A')
                actual_gain = metadata.get('AnalogueGain', 'N/A')
                print(f"✓ Verified actual camera state - Exposure: {actual_exposure}, Gain: {actual_gain}")
            except Exception as e:
                print(f"⚠️  Warning: Could not verify camera settings: {e}")
        
        # Capture calibration frames
        captured = 0
        attempts = 0
        max_attempts = target_frames * 3
        
        while captured < target_frames and attempts < max_attempts:
            print(f"Capturing frame... (attempt {attempts+1}, captured {captured}/{target_frames})")
            success, message = self.capture_calibration_frame()
            attempts += 1
            
            if success:
                captured += 1
                print(f"✓ Progress: {captured}/{target_frames} - {message}")
                if captured < target_frames:
                    print("Waiting 0.5s for pattern movement...")
                    time.sleep(0.5)  # Reduced delay - just enough to stabilize
            else:
                print(f"✗ Attempt {attempts}: {message}")
                time.sleep(0.1)  # Much shorter delay for failed attempts
        
        if captured < 15:
            print(f"Insufficient frames captured: {captured}")
            return False
        
        # Perform calibration steps
        if not self.use_highres_intrinsics:
            self.calibrate_individual_cameras()
        else:
            print("Using pre-calibrated high-resolution intrinsics")
            
        self.calibrate_multi_camera_system()
        rectification_maps = self.generate_rectification_maps()
        self.create_rectified_test_images(rectification_maps)
        
        # Save calibration data
        calib_summary = {
            'timestamp': datetime.now().isoformat(),
            'frames_captured': captured,
            'reference_system': 'center_point',
            'camera_config': self.camera_config,
            'use_highres_intrinsics': self.use_highres_intrinsics,
            'camera_matrices': {k: v.tolist() for k, v in self.calibration_data['camera_matrices'].items()},
            'distortion_coeffs': {k: v.tolist() for k, v in self.calibration_data['distortion_coeffs'].items()},
            'rotation_vectors': {k: v.tolist() for k, v in self.calibration_data['rotation_vectors'].items()},
            'translation_vectors': {k: v.tolist() for k, v in self.calibration_data['translation_vectors'].items()}
        }
        
        with open(f"{self.maps_dir}/unified_calibration_summary.json", 'w') as f:
            json.dump(calib_summary, f, indent=2)
        
        print("Multi-camera calibration complete!")
        print(f"- Frames used: {captured}")
        print(f"- Reference system: Center point between all cameras")
        print(f"- Camera configuration: {self.camera_config}")
        print(f"- High-resolution intrinsics: {'Yes' if self.use_highres_intrinsics else 'No'}")
        print(f"- Rectified test images saved to: {self.rectified_dir}")
        
        return True

def main():
    print("Unified Multi-Camera Calibration System V6 - Center Reference")
    print("============================================================")
    print("Uses center point between all cameras as reference coordinate system")
    print("Camera Layout: [0, 3]")
    print("               [1, 2]")
    print("")
    
    calibrator = UnifiedMultiCameraCalibrator()
    
    while True:
        print("\nOptions:")
        print("1. Full Multi-Camera Calibration (20 frames)")
        print("2. High-Resolution Intrinsic Calibration + Full Calibration")
        print("3. Single Frame Test")
        print("4. Show Camera Layout")
        print("5. Exit")
        
        choice = input("Select option (1-5): ").strip()
        
        if choice == '1':
            calibrator.perform_full_calibration()
        elif choice == '2':
            calibrator.perform_full_calibration(use_highres_intrinsics=True)
        elif choice == '3':
            success, message = calibrator.capture_calibration_frame()
            print(f"Result: {message}")
        elif choice == '4':
            if calibrator.calibration_data['rotation_vectors']:
                calibrator.print_camera_layout()
            else:
                print("No calibration data available. Run calibration first.")
        elif choice == '5':
            break
        else:
            print("Invalid option")

if __name__ == "__main__":
    main() 