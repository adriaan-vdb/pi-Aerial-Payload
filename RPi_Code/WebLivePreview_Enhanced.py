import time
import cv2
import numpy as np
from picamera2 import Picamera2
from flask import Flask, render_template, Response, request, jsonify
import threading
import os
from datetime import datetime
import io
import base64

# UI Color Configuration
UI_COLOR = (31, 31, 186)  # Green color for all text overlays (BGR format)

# Camera Configuration Matrix - Change this to reorder cameras in the 2x2 grid
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

# Global camera settings
CAMERA_SETTINGS = {
    "exposure_time": 10000,    # 5ms exposure time
    "analogue_gain": 1.5,     # Unity gain
    "contrast": 1.2           # Default contrast
}

app = Flask(__name__)

class EnhancedQuadCamStreamer:
    def __init__(self):
        self.camera = None
        self.is_streaming = False
        self.capture_count = 0
        self.capture_dir = "/home/av/Documents/pi-Aerial-Payload/captures/web_preview"
        self.brightness_compensation_enabled = True
        
        # Create capture directory
        if not os.path.exists(self.capture_dir):
            os.makedirs(self.capture_dir)
        
        self.setup_camera()
    
    def setup_camera(self):
        """Initialize the camera with fixed exposure and contrast settings"""
        try:
            self.camera = Picamera2()
            
            # OV9281 optimized manual exposure and contrast settings
            # Safe exposure range: 100μs - 100,000μs (0.1ms - 100ms)
            basic_controls = {
                "ExposureTime": CAMERA_SETTINGS["exposure_time"],
                "AnalogueGain": CAMERA_SETTINGS["analogue_gain"],
                "Contrast": CAMERA_SETTINGS["contrast"]
            }
            
            # Try to add optional controls if available
            try:
                # Check what controls are available
                camera_controls = self.camera.camera_controls
                if "AeEnable" in camera_controls:
                    basic_controls["AeEnable"] = False
                if "AwbEnable" in camera_controls:
                    basic_controls["AwbEnable"] = False
                print(f"Available camera controls: {list(camera_controls.keys())}")
            except Exception as e:
                print(f"Could not check camera controls: {e}")
            
            # Configure for live preview with manual exposure and contrast control
            preview_config = self.camera.create_preview_configuration(
                main={"size": (1280, 200)},  # Reduced resolution for web streaming
                lores={"size": (640, 100)},   # Even smaller for display
                controls=basic_controls
            )
            self.camera.configure(preview_config)
            
            # Create capture configuration (full resolution)
            self.capture_config = self.camera.create_still_configuration(
                main={"size": (2560, 400)},
                controls=basic_controls
            )
            
            self.camera.start()
            
            # Apply controls after starting
            self.camera.set_controls(basic_controls)
            
            self.is_streaming = True
            print("Camera initialized successfully with fixed exposure and contrast settings")
            
        except Exception as e:
            print(f"Error initializing camera: {e}")
            self.is_streaming = False
    
    def update_camera_controls(self):
        """Update camera controls with current settings"""
        if not self.camera:
            return False
        
        try:
            controls = {
                "ExposureTime": CAMERA_SETTINGS["exposure_time"],
                "AnalogueGain": CAMERA_SETTINGS["analogue_gain"],
                "Contrast": CAMERA_SETTINGS["contrast"]
            }
            
            # Add optional controls if available
            try:
                camera_controls = self.camera.camera_controls
                if "AeEnable" in camera_controls:
                    controls["AeEnable"] = False
                if "AwbEnable" in camera_controls:
                    controls["AwbEnable"] = False
            except:
                pass
            
            self.camera.set_controls(controls)
            return True
            
        except Exception as e:
            print(f"Error updating camera controls: {e}")
            return False
    
    def apply_brightness_compensation(self, frame):
        """Apply brightness compensation to individual camera regions"""
        if not self.brightness_compensation_enabled:
            return frame
            
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
            brightness_factor = comp_settings["exposure_multiplier"]
            
            # Apply brightness compensation using gamma correction
            if brightness_factor != 1.0:
                # Calculate gamma for brightness adjustment
                gamma = 1.0 / brightness_factor if brightness_factor > 1.0 else 1.0 + (1.0 - brightness_factor)
                
                # Build lookup table for gamma correction
                lookup_table = np.array([((i / 255.0) ** gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
                
                # Apply gamma correction
                compensated_region = cv2.LUT(camera_region, lookup_table)
                
                # Additional brightness scaling if needed
                if brightness_factor > 1.0:
                    compensated_region = cv2.convertScaleAbs(compensated_region, alpha=brightness_factor, beta=0)
            else:
                compensated_region = camera_region
            
            # Put compensated region back
            compensated_frame[0:camera_height, x_start:x_end] = compensated_region
        
        return compensated_frame
    
    def get_frame(self):
        """Get a frame from the camera and arrange as 2x2 grid"""
        if not self.is_streaming or not self.camera:
            return None
        
        try:
            # Capture frame (2560x400 - all 4 cameras combined)
            frame = self.camera.capture_array()
            
            # Convert from RGB to BGR for OpenCV
            if len(frame.shape) == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Apply brightness compensation
            frame = self.apply_brightness_compensation(frame)
            
            # Split the combined frame into individual camera feeds
            camera_width = frame.shape[1] // 4  # 640 (for 2560) or 320 (for 1280)
            camera_height = frame.shape[0]      # 400 (for full) or 200 (for preview)
            
            cameras = []
            for i in range(4):
                x_start = i * camera_width
                x_end = (i + 1) * camera_width
                camera_frame = frame[0:camera_height, x_start:x_end]
                
                # Camera labels and overlays removed for clean view
                
                cameras.append(camera_frame)
            
            # Arrange cameras in 2x2 grid according to CAMERA_CONFIG
            top_left = cameras[CAMERA_CONFIG[0][0]]
            top_right = cameras[CAMERA_CONFIG[0][1]]
            top_row = np.hstack([top_left, top_right])
            
            bottom_left = cameras[CAMERA_CONFIG[1][0]]
            bottom_right = cameras[CAMERA_CONFIG[1][1]]
            bottom_row = np.hstack([bottom_left, bottom_right])
            
            # Combine top and bottom rows
            grid_frame = np.vstack([top_row, bottom_row])
            
            return grid_frame
            
        except Exception as e:
            print(f"Error capturing frame: {e}")
            return None
    
    def capture_image(self):
        """Capture a full resolution image with brightness compensation"""
        if not self.camera:
            return False, "Camera not initialized"
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.capture_dir}/capture_{timestamp}.png"
            
            print("Capturing full resolution image with brightness compensation...")
            
            # Stop camera to allow configuration change
            self.camera.stop()
            
            # Configure capture mode for full resolution
            self.camera.configure(self.capture_config)
            self.camera.start()
            
            # Apply current controls
            self.update_camera_controls()
            
            # Wait for camera to stabilize
            time.sleep(1)
            
            # Capture raw image
            raw_frame = self.camera.capture_array()
            
            # Convert from RGB to BGR
            if len(raw_frame.shape) == 3:
                raw_frame = cv2.cvtColor(raw_frame, cv2.COLOR_RGB2BGR)
            
            # Apply brightness compensation
            compensated_frame = self.apply_brightness_compensation(raw_frame)
            
            # Save the compensated image
            cv2.imwrite(filename, compensated_frame)
            self.capture_count += 1
            
            # Switch back to preview configuration
            self.camera.stop()
            
            # Use same OV9281 optimized controls as setup
            basic_controls = {
                "ExposureTime": CAMERA_SETTINGS["exposure_time"],
                "AnalogueGain": CAMERA_SETTINGS["analogue_gain"],
                "Contrast": CAMERA_SETTINGS["contrast"]
            }
            try:
                camera_controls = self.camera.camera_controls
                if "AeEnable" in camera_controls:
                    basic_controls["AeEnable"] = False
                if "AwbEnable" in camera_controls:
                    basic_controls["AwbEnable"] = False
            except:
                pass
                
            preview_config = self.camera.create_preview_configuration(
                main={"size": (1280, 200)},
                lores={"size": (640, 100)},
                controls=basic_controls
            )
            self.camera.configure(preview_config)
            self.camera.start()
            
            # Apply controls after starting
            self.camera.set_controls(basic_controls)
            
            print(f"Brightness-compensated capture complete: {filename}")
            return True, f"Captured: {filename} (Full resolution 2560x400 with brightness compensation)"
            
        except Exception as e:
            # Ensure we're back in preview mode
            try:
                self.camera.stop()
                
                # Use OV9281 optimized controls for error recovery
                basic_controls = {
                    "ExposureTime": CAMERA_SETTINGS["exposure_time"],
                    "AnalogueGain": CAMERA_SETTINGS["analogue_gain"],
                    "Contrast": CAMERA_SETTINGS["contrast"]
                }
                try:
                    camera_controls = self.camera.camera_controls
                    if "AeEnable" in camera_controls:
                        basic_controls["AeEnable"] = False
                    if "AwbEnable" in camera_controls:
                        basic_controls["AwbEnable"] = False
                except:
                    pass
                    
                preview_config = self.camera.create_preview_configuration(
                    main={"size": (1280, 200)},
                    lores={"size": (640, 100)},
                    controls=basic_controls
                )
                self.camera.configure(preview_config)
                self.camera.start()
                self.camera.set_controls(basic_controls)
            except:
                pass
            return False, f"Error capturing image: {e}"
    
    def get_brightness_settings(self):
        """Get current brightness compensation settings"""
        return BRIGHTNESS_COMPENSATION
    
    def get_camera_settings(self):
        """Get current camera settings"""
        return CAMERA_SETTINGS
    
    def update_brightness_setting(self, camera_id, setting_type, value):
        """Update brightness compensation for a specific camera"""
        if 0 <= camera_id <= 3 and setting_type in ["exposure_multiplier", "gain_multiplier"]:
            BRIGHTNESS_COMPENSATION[camera_id][setting_type] = value
            return True
        return False
    
    def update_camera_setting(self, setting_type, value):
        """Update global camera settings (affects all cameras)"""
        if setting_type in ["exposure_time", "analogue_gain", "contrast"]:
            CAMERA_SETTINGS[setting_type] = value
            success = self.update_camera_controls()
            return success
        return False
    
    def toggle_brightness_compensation(self):
        """Toggle brightness compensation on/off"""
        self.brightness_compensation_enabled = not self.brightness_compensation_enabled
        return self.brightness_compensation_enabled
    
    def stop_camera(self):
        """Stop the camera"""
        if self.camera:
            self.camera.stop()
            self.is_streaming = False

# Global camera instance
camera_streamer = EnhancedQuadCamStreamer()

def generate_frames():
    """Generate frames for the video stream"""
    while True:
        frame = camera_streamer.get_frame()
        if frame is not None:
            # Encode frame to JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.1)  # ~10 FPS

@app.route('/')
def index():
    """Main page with camera controls"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enhanced QuadCam Web Preview</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <style>
            body { 
                font-family: Arial, sans-serif; 
                background-color: #f0f0f0; 
                margin: 0; 
                padding: 20px;
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                background-color: white; 
                padding: 20px; 
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }
            h1 { 
                color: #333; 
                text-align: center; 
                margin-bottom: 20px;
            }
            .video-container { 
                text-align: center; 
                margin: 20px 0; 
            }
            .controls { 
                text-align: center; 
                margin: 20px 0; 
            }
            button { 
                background-color: #4CAF50; 
                color: white; 
                padding: 10px 20px; 
                border: none; 
                border-radius: 5px; 
                cursor: pointer; 
                font-size: 16px; 
                margin: 5px;
            }
            button:hover { 
                background-color: #45a049; 
            }
            .settings-section {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }
            .settings-section h3 {
                margin-top: 0;
                color: #333;
            }
            .global-controls {
                background-color: #e8f4f8;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }
            .global-controls h3 {
                margin-top: 0;
                color: #333;
            }
            .control-group {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin: 15px 0;
            }
            .control-item {
                background-color: white;
                padding: 15px;
                border-radius: 5px;
                border: 1px solid #ddd;
            }
            .control-item h4 {
                margin: 0 0 10px 0;
                color: #555;
            }
            .slider-container {
                margin: 10px 0;
            }
            .slider-container label {
                display: block;
                font-size: 14px;
                color: #666;
                margin-bottom: 5px;
            }
            .slider {
                width: 100%;
                height: 20px;
                border-radius: 10px;
                background: #ddd;
                outline: none;
                -webkit-appearance: none;
            }
            .slider::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: #4CAF50;
                cursor: pointer;
            }
            .status { 
                text-align: center; 
                margin: 10px 0; 
                padding: 10px; 
                border-radius: 5px; 
            }
            .success { 
                background-color: #d4edda; 
                color: #155724; 
                border: 1px solid #c3e6cb; 
            }
            .error { 
                background-color: #f8d7da; 
                color: #721c24; 
                border: 1px solid #f5c6cb; 
            }
            img { 
                max-width: 100%; 
                height: auto; 
                border: 2px solid #ddd; 
                border-radius: 5px; 
            }
            .value-display {
                font-weight: bold;
                color: #333;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Enhanced QuadCam Web Live Preview</h1>
            <div class="video-container">
                <img src="/video_feed" alt="Camera Feed" id="cameraFeed" />
            </div>
            
            <div class="controls">
                <button onclick="captureImage()">Capture Image</button>
                <button onclick="refreshFeed()">Refresh Feed</button>
                <button onclick="toggleBrightnessCompensation()">Toggle Brightness Compensation</button>
                <button onclick="resetAllSettings()">Reset All Settings</button>
            </div>
            
            <div class="global-controls">
                <h3>Global Camera Settings (All Cameras)</h3>
                <div class="control-group">
                                         <div class="control-item">
                         <h4>Exposure Time</h4>
                         <div class="slider-container">
                             <label>Exposure: <span id="exposure-value" class="value-display">10000</span> μs</label>
                             <input type="range" min="100" max="100000" step="100" value="10000" 
                                    class="slider" id="exposure-slider" onchange="updateCameraSetting('exposure_time', parseInt(this.value))">
                         </div>
                     </div>
                     <div class="control-item">
                         <h4>Analogue Gain</h4>
                         <div class="slider-container">
                             <label>Gain: <span id="gain-value" class="value-display">1.5</span></label>
                             <input type="range" min="1.0" max="16.0" step="0.25" value="1.5" 
                                    class="slider" id="gain-slider" onchange="updateCameraSetting('analogue_gain', parseFloat(this.value))">
                         </div>
                     </div>
                     <div class="control-item">
                         <h4>Contrast</h4>
                         <div class="slider-container">
                             <label>Contrast: <span id="contrast-value" class="value-display">1.2</span></label>
                             <input type="range" min="0.0" max="10.0" step="0.25" value="1.2" 
                                    class="slider" id="contrast-slider" onchange="updateCameraSetting('contrast', parseFloat(this.value))">
                         </div>
                     </div>
                </div>
            </div>
            
            <div class="settings-section">
                <h3>Individual Camera Brightness Compensation</h3>
                <p>Adjust individual camera brightness to compensate for differences.</p>
                <div class="control-group">
                    <div class="control-item">
                        <h4>Camera 0</h4>
                        <div class="slider-container">
                            <label>Exposure Multiplier: <span id="cam0-exp-value" class="value-display">1.0</span></label>
                            <input type="range" min="0.5" max="2.0" step="0.1" value="1.0" 
                                   class="slider" id="cam0-exp" onchange="updateBrightness(0, 'exposure_multiplier', this.value)">
                        </div>
                    </div>
                    <div class="control-item">
                        <h4>Camera 1</h4>
                        <div class="slider-container">
                            <label>Exposure Multiplier: <span id="cam1-exp-value" class="value-display">0.8</span></label>
                            <input type="range" min="0.5" max="2.0" step="0.1" value="0.8" 
                                   class="slider" id="cam1-exp" onchange="updateBrightness(1, 'exposure_multiplier', this.value)">
                        </div>
                    </div>
                    <div class="control-item">
                        <h4>Camera 2</h4>
                        <div class="slider-container">
                            <label>Exposure Multiplier: <span id="cam2-exp-value" class="value-display">1.4</span></label>
                            <input type="range" min="0.5" max="2.0" step="0.1" value="1.4" 
                                   class="slider" id="cam2-exp" onchange="updateBrightness(2, 'exposure_multiplier', this.value)">
                        </div>
                    </div>
                    <div class="control-item">
                        <h4>Camera 3</h4>
                        <div class="slider-container">
                            <label>Exposure Multiplier: <span id="cam3-exp-value" class="value-display">1.2</span></label>
                            <input type="range" min="0.5" max="2.0" step="0.1" value="1.2" 
                                   class="slider" id="cam3-exp" onchange="updateBrightness(3, 'exposure_multiplier', this.value)">
                        </div>
                    </div>
                </div>
            </div>
            
            <div id="status" class="status" style="display: none;"></div>
            
            <!-- Live Status Information -->
            <div style="text-align: center; margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                <p style="margin: 0; font-size: 1.1em; color: #333;">
                    <strong>Date:</strong> <span id="currentDate">--/--/--</span> | 
                    <strong>Time:</strong> <span id="currentTime">--:--:--</span> | 
                    <strong>Captures:</strong> <span id="captureCount">0</span>
                </p>
            </div>
        </div>
        
        <script>
            function captureImage() {
                fetch('/capture', {method: 'POST'})
                    .then(response => response.json())
                    .then(data => {
                        const statusDiv = document.getElementById('status');
                        statusDiv.style.display = 'block';
                        if (data.success) {
                            statusDiv.className = 'status success';
                            statusDiv.textContent = data.message;
                        } else {
                            statusDiv.className = 'status error';
                            statusDiv.textContent = data.message;
                        }
                        setTimeout(() => {
                            statusDiv.style.display = 'none';
                        }, 3000);
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        showStatus('Error capturing image', 'error');
                    });
            }
            
            function refreshFeed() {
                const img = document.getElementById('cameraFeed');
                const currentSrc = img.src;
                img.src = '';
                setTimeout(() => {
                    img.src = currentSrc + '?t=' + new Date().getTime();
                }, 100);
            }
            
            function toggleBrightnessCompensation() {
                fetch('/toggle_brightness_compensation', {method: 'POST'})
                    .then(response => response.json())
                    .then(data => {
                        showStatus(data.message, data.success ? 'success' : 'error');
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        showStatus('Error toggling brightness compensation', 'error');
                    });
            }
            
            function updateBrightness(cameraId, settingType, value) {
                fetch('/update_brightness', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        camera_id: cameraId,
                        setting_type: settingType,
                        value: parseFloat(value)
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById(`cam${cameraId}-exp-value`).textContent = value;
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                });
            }
            
            function updateCameraSetting(settingType, value) {
                fetch('/update_camera_setting', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        setting_type: settingType,
                        value: value
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Update the display value
                        if (settingType === 'exposure_time') {
                            document.getElementById('exposure-value').textContent = value;
                        } else if (settingType === 'analogue_gain') {
                            document.getElementById('gain-value').textContent = value;
                        } else if (settingType === 'contrast') {
                            document.getElementById('contrast-value').textContent = value;
                        }
                        showStatus(`Updated ${settingType} to ${value}`, 'success');
                    } else {
                        showStatus(`Failed to update ${settingType}`, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showStatus(`Error updating ${settingType}`, 'error');
                });
            }
            
            function resetAllSettings() {
                // Reset global settings
                document.getElementById('exposure-slider').value = 10000;
                document.getElementById('gain-slider').value = 1.5;
                document.getElementById('contrast-slider').value = 1.2;
                updateCameraSetting('exposure_time', 10000);
                updateCameraSetting('analogue_gain', 1.5);
                updateCameraSetting('contrast', 1.2);
                
                // Reset brightness compensation
                const defaults = {0: 1.0, 1: 0.8, 2: 1.4, 3: 1.2};
                for (let i = 0; i < 4; i++) {
                    document.getElementById(`cam${i}-exp`).value = defaults[i];
                    updateBrightness(i, 'exposure_multiplier', defaults[i]);
                }
                
                showStatus('All settings reset to defaults', 'success');
            }
            
            function showStatus(message, type) {
                const statusDiv = document.getElementById('status');
                statusDiv.style.display = 'block';
                statusDiv.className = `status ${type}`;
                statusDiv.textContent = message;
                setTimeout(() => {
                    statusDiv.style.display = 'none';
                }, 3000);
            }
            
            function updateStatus() {
                const now = new Date();
                const dateString = now.toLocaleDateString();
                const timeString = now.toLocaleTimeString();
                document.getElementById('currentDate').textContent = dateString;
                document.getElementById('currentTime').textContent = timeString;
                
                fetch('/status')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('captureCount').textContent = data.capture_count;
                    })
                    .catch(error => {
                        console.error('Error fetching status:', error);
                    });
            }
            
            // Update status every second
            setInterval(updateStatus, 1000);
            updateStatus();
        </script>
    </body>
    </html>
    '''

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture():
    """Capture image route"""
    success, message = camera_streamer.capture_image()
    return jsonify({'success': success, 'message': message})

@app.route('/status')
def status():
    """Status information route"""
    return jsonify({
        'capture_count': camera_streamer.capture_count,
        'brightness_compensation_enabled': camera_streamer.brightness_compensation_enabled,
        'brightness_settings': camera_streamer.get_brightness_settings(),
        'camera_settings': camera_streamer.get_camera_settings()
    })

@app.route('/toggle_brightness_compensation', methods=['POST'])
def toggle_brightness_compensation():
    """Toggle brightness compensation"""
    enabled = camera_streamer.toggle_brightness_compensation()
    return jsonify({
        'success': True,
        'message': f"Brightness compensation {'enabled' if enabled else 'disabled'}",
        'enabled': enabled
    })

@app.route('/update_brightness', methods=['POST'])
def update_brightness():
    """Update brightness compensation settings"""
    data = request.json
    camera_id = data.get('camera_id')
    setting_type = data.get('setting_type')
    value = data.get('value')
    
    success = camera_streamer.update_brightness_setting(camera_id, setting_type, value)
    return jsonify({
        'success': success,
        'message': f"Updated camera {camera_id} {setting_type} to {value}" if success else "Failed to update setting"
    })

@app.route('/update_camera_setting', methods=['POST'])
def update_camera_setting():
    """Update global camera settings"""
    data = request.json
    setting_type = data.get('setting_type')
    value = data.get('value')
    
    success = camera_streamer.update_camera_setting(setting_type, value)
    return jsonify({
        'success': success,
        'message': f"Updated {setting_type} to {value}" if success else f"Failed to update {setting_type}"
    })

if __name__ == '__main__':
    try:
        print("Starting Enhanced QuadCam Web Preview...")
        print("Camera initializing with brightness compensation and contrast control...")
        
        if camera_streamer.is_streaming:
            print("Camera initialized successfully")
            print("Brightness compensation and contrast control enabled")
            print("Starting web server...")
            print("Access the enhanced live preview at: http://your-pi-ip:5000")
            print("Or locally at: http://localhost:5000")
            print("Press Ctrl+C to stop")
            
            # Start Flask app
            app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
        else:
            print("Failed to initialize camera")
            
    except KeyboardInterrupt:
        print("\nStopping camera...")
        camera_streamer.stop_camera()
        print("Camera stopped")
    except Exception as e:
        print(f"Error: {e}")
        camera_streamer.stop_camera() 