import cv2
import numpy as np
from picamera2 import Picamera2
import time
import os

# UI Color Configuration
UI_COLOR = (31, 31, 186)  # Red color for all text overlays (BGR format)

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

def live_preview_with_capture():
    """
    Live preview with OpenCV that works over VNC
    Press 'c' to capture image, 'q' to quit
    """
    print("Starting live preview...")
    print("Controls:")
    print("  'c' - Capture image")
    print("  'q' - Quit")
    print("  'f' - Toggle fullscreen")
    print("  'ESC' - Exit fullscreen")
    
    # Initialize camera
    picam2 = Picamera2()
    
    # Configure for live preview (smaller resolution for smooth preview)
    preview_config = picam2.create_preview_configuration(
        main={"size": (1280, 200)},  # Half resolution for smooth preview
        lores={"size": (640, 100)}   # Even smaller for display
    )
    picam2.configure(preview_config)
    
    # Start camera
    picam2.start()
    
    # Create capture directory
    capture_dir = "/home/av/Documents/pi-Aerial-Payload/captures/live_preview"
    if not os.path.exists(capture_dir):
        os.makedirs(capture_dir)
    
    # Initialize variables
    capture_count = 0
    fullscreen = False
    window_name = "QuadCam Live Preview - 2x2 Grid"
    
    # Create window
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    try:
        while True:
            # Capture frame (2560x400 - all 4 cameras combined)
            frame = picam2.capture_array()
            
            # Convert from RGB to BGR for OpenCV
            if len(frame.shape) == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Split the combined frame into individual camera feeds and arrange as 2x2 grid
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
            
            # Resize for display if needed
            height, width = grid_frame.shape[:2]
            if width > 1920:  # If too wide for most screens
                scale = 1920 / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                grid_frame = cv2.resize(grid_frame, (new_width, new_height))
            
            # Add overall status text
            cv2.putText(grid_frame, f"'c' to capture (2560x400px)", 
                       (10, grid_frame.shape[0] - 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, UI_COLOR, 2)
            cv2.putText(grid_frame, f"Captures: {capture_count} | Press 'q' to quit", 
                       (10, grid_frame.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, UI_COLOR, 2)
            
            fullscreen_text = "Fullscreen: ON (press 'f')" if fullscreen else "Fullscreen: OFF (press 'f' to enter)"
            cv2.putText(grid_frame, fullscreen_text, 
                       (10, grid_frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, UI_COLOR, 2)
            
            # Use the processed grid frame for display
            frame = grid_frame
            
            # Display frame
            cv2.imshow(window_name, frame)
            
            # Check for key presses
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("Quitting...")
                break
            elif key == 27:  # ESC key
                if fullscreen:
                    print("Exiting fullscreen...")
                    cv2.destroyWindow(window_name)
                    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                    fullscreen = False
            elif key == ord('c'):
                # Capture full resolution image (2560x400)
                print("Capturing full resolution image...")
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"{capture_dir}/capture_{timestamp}.png"
                
                try:
                    # Stop camera to allow configuration change
                    picam2.stop()
                    
                    # Create and configure capture mode for full resolution
                    capture_config = picam2.create_still_configuration(
                        main={"size": (2560, 400)}  # Full resolution
                    )
                    picam2.configure(capture_config)
                    
                    # Start camera in capture mode
                    picam2.start()
                    
                    # Take the photo
                    picam2.capture_file(filename)
                    capture_count += 1
                    print(f"Full resolution captured: {filename}")
                    
                    # Stop camera again to reconfigure for preview
                    picam2.stop()
                    
                    # Switch back to preview configuration
                    preview_config = picam2.create_preview_configuration(
                        main={"size": (1280, 200)},
                        lores={"size": (640, 100)}
                    )
                    picam2.configure(preview_config)
                    
                    # Restart camera in preview mode
                    picam2.start()
                    
                except Exception as e:
                    print(f"Error capturing image: {e}")
                    # Try to restore preview configuration if capture failed
                    try:
                        picam2.stop()
                        preview_config = picam2.create_preview_configuration(
                            main={"size": (1280, 200)},
                            lores={"size": (640, 100)}
                        )
                        picam2.configure(preview_config)
                        picam2.start()
                    except:
                        print("Warning: Could not restore preview configuration")
                
            elif key == ord('f'):
                # Toggle fullscreen
                fullscreen = not fullscreen
                if fullscreen:
                    print("Entering fullscreen...")
                    cv2.destroyWindow(window_name)
                    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                else:
                    print("Exiting fullscreen...")
                    cv2.destroyWindow(window_name)
                    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        # Cleanup
        picam2.stop()
        cv2.destroyAllWindows()
        print(f"Session ended. Total captures: {capture_count}")

if __name__ == "__main__":
    live_preview_with_capture() 