import cv2
import numpy as np
import os
from datetime import datetime

def new_ndvi(nir, red):
    """Calculate NDVI using the formula (NIR - Red) / (NIR + Red)"""
    bottom = (nir.astype(float) + red.astype(float))
    bottom[bottom == 0] = np.finfo(float).eps  # Avoid division by zero
    ndvi = ((nir.astype(float) - red.astype(float)) / bottom)
    return ndvi

def contrast(im):
    """Apply contrast enhancement to image"""
    in_min = np.percentile(im, 5)
    in_max = np.percentile(im, 95)
    out_min = 0.0
    out_max = 255.0
    out = (im - in_min) * ((out_max - out_min) / (in_max - in_min)) + out_min
    # Clip values to ensure they are within [0, 255]
    out = np.clip(out, 0, 255)
    return out.astype(np.uint8)

def TotalNDVI(red_frame, nir_frame, image_count):
    """
    Process live NDVI calculation and save results
    
    Args:
        red_frame: Red channel image crop
        nir_frame: NIR channel image crop  
        image_count: Counter for naming saved files
    """
    try:
        # Ensure we have valid images
        if red_frame is None or nir_frame is None:
            print("Error: Invalid image frames provided to TotalNDVI")
            return
        
        # Apply contrast enhancement
        red_enhanced = contrast(red_frame)
        nir_enhanced = contrast(nir_frame)
        
        # Calculate NDVI
        ndvi = new_ndvi(nir_enhanced, red_enhanced)
        
        # Normalize NDVI to 0-255 range
        ndvi_normalized = cv2.normalize(ndvi, None, 0, 255, cv2.NORM_MINMAX)
        ndvi_uint8 = ndvi_normalized.astype(np.uint8)
        
        # Apply color mapping (using VIRIDIS colormap)
        fastiecm = cv2.COLORMAP_VIRIDIS
        colour_mapped_image = cv2.applyColorMap(ndvi_uint8, fastiecm)
        
        # Create results directories if they don't exist
        folder = "/home/av/Documents/pi-Aerial-Payload/results/ndvi"
        os.makedirs(folder, exist_ok=True)
        
        # Generate timestamp and filenames
        timestamp = datetime.now().strftime("%d_%H-%M-%S")
        ndvi_name = f"ColourNDVI_{timestamp}_{image_count}"
        ndvi_raw_name = f"NDVI_{timestamp}_{image_count}"
        
        # Save both color-mapped and raw NDVI images
        filepath_color = os.path.join(folder, ndvi_name + '.png')
        filepath_raw = os.path.join(folder, ndvi_raw_name + '.png')
        
        cv2.imwrite(filepath_color, colour_mapped_image)
        cv2.imwrite(filepath_raw, ndvi_uint8)
        
        print(f"NDVI images saved: {ndvi_name}")
        
        # Optional: Display the NDVI result
        cv2.imshow("Live NDVI", colour_mapped_image)
        cv2.waitKey(1)  # Non-blocking wait
        
    except Exception as e:
        print(f"Error in TotalNDVI processing: {e}")
        
def cleanup_ndvi_display():
    """Clean up NDVI display windows"""
    cv2.destroyWindow("Live NDVI") 