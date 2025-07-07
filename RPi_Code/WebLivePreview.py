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
# [Top-Left, Top-Right]
# [Bottom-Left, Bottom-Right]
# Camera numbers: 0=leftmost, 1=second, 2=third, 3=rightmost (in the combined 2560x400 image)

CAMERA_CONFIG = [
    [3, 0], 
    [2, 1] 
]

# Camera labels for overlay text
CAMERA_LABELS = ["Cam 0", "Cam 1", "Cam 2", "Cam 3"]

app = Flask(__name__)

class QuadCamStreamer:
    def __init__(self):
        self.camera = None
        self.is_streaming = False
        self.capture_count = 0
        self.capture_dir = "/home/av/Documents/pi-Aerial-Payload/captures/web_preview"
        
        # Create capture directory
        if not os.path.exists(self.capture_dir):
            os.makedirs(self.capture_dir)
        
        self.setup_camera()
    
    def setup_camera(self):
        """Initialize the camera"""
        try:
            self.camera = Picamera2()
            
            # Configure for live preview
            preview_config = self.camera.create_preview_configuration(
                main={"size": (1280, 200)},  # Reduced resolution for web streaming
                lores={"size": (640, 100)}   # Even smaller for display
            )
            self.camera.configure(preview_config)
            
            # Create capture configuration (full resolution)
            self.capture_config = self.camera.create_still_configuration(
                main={"size": (2560, 400)}
            )
            
            self.camera.start()
            self.is_streaming = True
            print("Camera initialized successfully")
            
        except Exception as e:
            print(f"Error initializing camera: {e}")
            self.is_streaming = False
    
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
            
            # Split the combined frame into individual camera feeds
            # Each camera is 640x400 (2560/4 = 640)
            camera_width = frame.shape[1] // 4  # 640
            camera_height = frame.shape[0]      # 400
            
            cameras = []
            for i in range(4):
                x_start = i * camera_width
                x_end = (i + 1) * camera_width
                camera_frame = frame[0:camera_height, x_start:x_end]
                
                # Add camera label
                cv2.putText(camera_frame, CAMERA_LABELS[i], 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, UI_COLOR, 2)
                
                cameras.append(camera_frame)
            
            # Arrange cameras in 2x2 grid according to CAMERA_CONFIG
            # Create top row
            top_left = cameras[CAMERA_CONFIG[0][0]]
            top_right = cameras[CAMERA_CONFIG[0][1]]
            top_row = np.hstack([top_left, top_right])
            
            # Create bottom row
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
        """Capture a full resolution image (2560x400)"""
        if not self.camera:
            return False, "Camera not initialized"
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.capture_dir}/capture_{timestamp}.png"
            
            print("Capturing full resolution image...")
            
            # Stop camera to allow configuration change
            self.camera.stop()
            
            # Create and configure capture mode for full resolution
            capture_config = self.camera.create_still_configuration(
                main={"size": (2560, 400)}  # Full resolution
            )
            self.camera.configure(capture_config)
            
            # Start camera in capture mode
            self.camera.start()
            
            # Take the photo
            self.camera.capture_file(filename)
            self.capture_count += 1
            
            # Stop camera again to reconfigure for preview
            self.camera.stop()
            
            # Switch back to preview configuration
            preview_config = self.camera.create_preview_configuration(
                main={"size": (1280, 200)},
                lores={"size": (640, 100)}
            )
            self.camera.configure(preview_config)
            
            # Restart camera in preview mode
            self.camera.start()
            
            print(f"Full resolution capture complete: {filename}")
            return True, f"Captured: {filename} (Full resolution 2560x400)"
            
        except Exception as e:
            # If capture fails, ensure we're back in preview mode
            try:
                self.camera.stop()
                preview_config = self.camera.create_preview_configuration(
                    main={"size": (1280, 200)},
                    lores={"size": (640, 100)}
                )
                self.camera.configure(preview_config)
                self.camera.start()
            except:
                pass
            return False, f"Error capturing image: {e}"
    
    def stop_camera(self):
        """Stop the camera"""
        if self.camera:
            self.camera.stop()
            self.is_streaming = False

# Global camera instance
camera_streamer = QuadCamStreamer()

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
        <title>QuadCam Web Preview</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
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
            
            /* Mobile-specific styles */
            @media (max-width: 768px) {
                .container {
                    padding: 10px;
                    margin: 10px;
                }
                
                h1 {
                    font-size: 1.5em;
                    margin-bottom: 10px;
                }
                
                button {
                    padding: 15px 20px;
                    font-size: 16px;
                    margin: 8px 4px;
                    min-height: 44px; /* Touch-friendly size */
                }
                
                .controls {
                    flex-wrap: wrap;
                    display: flex;
                    justify-content: center;
                }
                
                .video-container {
                    margin: 10px 0;
                }
                
                .fullscreen-image {
                    position: fixed !important;
                    top: 0 !important;
                    left: 0 !important;
                    width: 100vw !important;
                    height: 100vh !important;
                    object-fit: contain !important;
                    z-index: 9999 !important;
                    background-color: black !important;
                    border: none !important;
                    border-radius: 0 !important;
                }
                
                table {
                    font-size: 0.9em;
                }
                
                table td {
                    padding: 8px !important;
                }
            }
            
            /* Portrait orientation on mobile */
            @media (max-width: 768px) and (orientation: portrait) {
                .container {
                    max-width: 100%;
                }
                
                img {
                    max-height: 40vh;
                }
            }
            
            /* Landscape orientation on mobile */
            @media (max-width: 768px) and (orientation: landscape) {
                .container {
                    max-width: 100%;
                }
                
                img {
                    max-height: 60vh;
                }
                
                .fullscreen-image {
                    width: 100vw !important;
                    height: 100vh !important;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>QuadCam Web Live Preview Grid</h1>
            <div class="video-container">
                <img src="/video_feed" alt="Camera Feed" id="cameraFeed" />
            </div>
            <div class="controls">
                <button onclick="captureImage()">Capture Image</button>
                <button onclick="refreshFeed()">Refresh Feed</button>
                <button onclick="toggleFullscreen()">Fullscreen</button>
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
                        const statusDiv = document.getElementById('status');
                        statusDiv.style.display = 'block';
                        statusDiv.className = 'status error';
                        statusDiv.textContent = 'Error capturing image';
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
            
            function toggleFullscreen() {
                const img = document.getElementById('cameraFeed');
                
                // Check if we're already in fullscreen
                if (document.fullscreenElement || document.webkitFullscreenElement || 
                    document.mozFullScreenElement || document.msFullscreenElement ||
                    img.classList.contains('fullscreen-image')) {
                    
                    // Exit fullscreen
                    if (document.exitFullscreen) {
                        document.exitFullscreen();
                    } else if (document.webkitExitFullscreen) {
                        document.webkitExitFullscreen();
                    } else if (document.mozCancelFullScreen) {
                        document.mozCancelFullScreen();
                    } else if (document.msExitFullscreen) {
                        document.msExitFullscreen();
                    }
                    
                    // Remove mobile fullscreen class
                    img.classList.remove('fullscreen-image');
                    document.body.style.overflow = 'auto';
                    
                } else {
                    // Enter fullscreen
                    
                    // Try native fullscreen API first
                    let fullscreenPromise = null;
                    
                    if (img.requestFullscreen) {
                        fullscreenPromise = img.requestFullscreen();
                    } else if (img.webkitRequestFullscreen) {
                        fullscreenPromise = img.webkitRequestFullscreen();
                    } else if (img.mozRequestFullScreen) {
                        fullscreenPromise = img.mozRequestFullScreen();
                    } else if (img.msRequestFullscreen) {
                        fullscreenPromise = img.msRequestFullscreen();
                    }
                    
                    // If native fullscreen fails or isn't available (mobile Safari), use CSS fallback
                    if (!fullscreenPromise) {
                        img.classList.add('fullscreen-image');
                        document.body.style.overflow = 'hidden';
                    } else {
                        // Handle fullscreen promise rejection (e.g., mobile Safari)
                        fullscreenPromise.catch(() => {
                            img.classList.add('fullscreen-image');
                            document.body.style.overflow = 'hidden';
                        });
                    }
                }
            }
            
            // Handle fullscreen change events
            function handleFullscreenChange() {
                const img = document.getElementById('cameraFeed');
                if (!(document.fullscreenElement || document.webkitFullscreenElement || 
                      document.mozFullScreenElement || document.msFullscreenElement)) {
                    img.classList.remove('fullscreen-image');
                    document.body.style.overflow = 'auto';
                }
            }
            
            // Add fullscreen event listeners
            document.addEventListener('fullscreenchange', handleFullscreenChange);
            document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
            document.addEventListener('mozfullscreenchange', handleFullscreenChange);
            document.addEventListener('MSFullscreenChange', handleFullscreenChange);
            
            // Handle escape key and back button on mobile
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    const img = document.getElementById('cameraFeed');
                    if (img.classList.contains('fullscreen-image')) {
                        img.classList.remove('fullscreen-image');
                        document.body.style.overflow = 'auto';
                    }
                }
            });
            
            // Handle touch events for mobile fullscreen exit
            document.addEventListener('touchstart', function(e) {
                const img = document.getElementById('cameraFeed');
                if (img.classList.contains('fullscreen-image') && e.touches.length === 2) {
                    // Double tap to exit fullscreen
                    img.classList.remove('fullscreen-image');
                    document.body.style.overflow = 'auto';
                }
            });
            
            function updateStatus() {
                // Update current date and time
                const now = new Date();
                const dateString = now.toLocaleDateString();
                const timeString = now.toLocaleTimeString();
                document.getElementById('currentDate').textContent = dateString;
                document.getElementById('currentTime').textContent = timeString;
                
                // Update capture count from server
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
            
            // Initial status update
            updateStatus();
        </script>
    </body>
    </html>
    '''

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture():
    """Capture image route"""
    success, message = camera_streamer.capture_image()
    return jsonify({'success': success, 'message': message})

@app.route('/status', methods=['GET'])
def status():
    """Get current status"""
    return jsonify({'capture_count': camera_streamer.capture_count})

if __name__ == '__main__':
    try:
        print("Starting QuadCam Web Preview...")
        print("Camera initializing...")
        
        if camera_streamer.is_streaming:
            print("✅ Camera initialized successfully")
            print("🌐 Starting web server...")
            print("📱 Access the live preview at: http://your-pi-ip:5000")
            print("🖥️  Or locally at: http://localhost:5000")
            print("⚡ Press Ctrl+C to stop")
            
            # Start Flask app
            app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
        else:
            print("❌ Failed to initialize camera")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping camera...")
        camera_streamer.stop_camera()
        print("✅ Camera stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        camera_streamer.stop_camera() 