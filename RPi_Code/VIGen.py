import cv2
import numpy as np
import os
import glob
#from fastiecm import fastiecm


fastiecm = cv2.COLORMAP_VIRIDIS   
# Updated paths to use correct user directory structure
imagesLeft = sorted(glob.glob("/home/av/Documents/pi-Aerial-Payload/captures/split"+'/*0.png'))
imagesRight= sorted(glob.glob("/home/av/Documents/pi-Aerial-Payload/captures/split"+'/*3.png'))
red_cap = sorted(glob.glob("/home/av/Documents/pi-Aerial-Payload/captures/split"+'/*1.png'))
nir_cap = sorted(glob.glob("/home/av/Documents/pi-Aerial-Payload/captures/split"+'/*2.png'))
def new_ndvi(nir,red):
    #needs to do ndvi calc =(nir -r)/(nir+r)
    #nir = img1
    #red = img2
    bottom = (nir.astype(float) + red.astype(float))
    bottom[bottom == 0] = np.finfo(float).eps
    ndvi =((nir.astype(float)-red.astype(float))/bottom)
    return ndvi

  # Flag to indicate whether to save the image or not

def contrast(im):
    in_min = np.percentile(im, 5)
    in_max = np.percentile(im, 95)
    out_min = 0.0
    out_max = 255.0
    out = (im - in_min) * ((out_max - out_min) / (in_max - in_min)) + out_min
    # Clip values to ensure they are within [0, 255]
    out = np.clip(out, 0, 255)
    return out.astype(np.uint8)
def NDVI(imagesLeft, imagesRight, mount):
    save_image = False
    
    for i, (imgLeft, imgRight) in enumerate(zip(imagesLeft, imagesRight)):
        red = cv2.imread(imgLeft)
        nir = cv2.imread(imgRight)

        if red is None or nir is None:
            print(f"Could not read images: {imgLeft}, {imgRight}")
            continue

        print(red.shape)
        #redCont = contrast(red)
        nirCont = contrast(nir)
        #cv2.imshow("controa",nirCont)
        ndvi = new_ndvi(nirCont, red)
        cv2.imshow("NDVI", ndvi)
        #crop = ndvi[0:350,10:600] #height width
        ndvi_normalized = cv2.normalize(ndvi, None, 0, 255, cv2.NORM_MINMAX)
        #cv2.imshow("normalized",ndvi_normalized)
        ndvi_uint8 = ndvi_normalized.astype(np.uint8)
        #cv2.imshow("uint",ndvi_uint8)
        colour_mapped_image = cv2.applyColorMap(ndvi_uint8, fastiecm)
        ndvi_save = cv2.normalize(colour_mapped_image, None, 0, 255, cv2.NORM_MINMAX)
        cv2.imshow("Colour",colour_mapped_image)
            
        key = cv2.waitKey(0)

        cv2.destroyAllWindows()  # Close window after key is pressed

        if key == ord('q'):  # Press 'q' to quit
            break
        elif key == ord('c'):  # Press 'c' to capture image
            save_image = True

        if save_image:
            ndvi_name = f"ColourNDVI{mount}_{i}"
            ndvi = f"NDVI{mount}_{i}"
            # Updated folder to use correct user directory
            folder = "/home/av/Documents/pi-Aerial-Payload/results/vegetation_indices"
            
            # Ensure vegetation indices directory exists
            os.makedirs(folder, exist_ok=True)
            
            filepath = os.path.join(folder, ndvi_name + '.png')
            filepath2 = os.path.join(folder, ndvi+ '.png')
            cv2.imwrite(filepath,colour_mapped_image)
            cv2.imwrite(filepath2, ndvi_uint8)
            print(f"NDVI image {ndvi_name} saved.")
            save_image = False  # Reset the flag after saving the image

if len(red_cap) > 0 and len(nir_cap) > 0:
    print(f"Processing {len(red_cap)} images for vegetation index generation...")
    NDVI(red_cap, nir_cap, "cap")
    NDVI(imagesLeft,imagesRight, "Internal")
else:
    print("No images found for processing. Please check the captures/split directory.")

'''

for i, (imgLeft, imgRight) in enumerate(zip(imagesLeft, imagesRight)):
    red = cv2.imread(imgLeft)
    nir = cv2.imread(imgRight)
    ndvi = new_ndvi(nir, red)
    cv2.imshow("NDVI", ndvi)
    cv2.waitKey(0)
    key = cv2.waitKey(1)
    #cv2.destroyAllWindows()
    # Save the NDVI image
    
    crop = ndvi[0:640,100:640] #height width
    colour_prep = crop.astype(np.uint8)
    colour_mapped_image = cv2.applyColorMap(colour_prep, fastiecm)
    cv2.imshow("Colour",colour_mapped_image)

    if key == ord('q'):  # Press 'q' to quit
        break
    elif key == ord('c'):  # Press 'c' to capture image
        ndvi_name = f"NDVI_{i}"
        folder = "NDVI"
        filepath = os.path.join(folder, ndvi_name + '.png')
    #cv2.imwrite(filepath, 255*ndvi)
        print(f"NDVI image {ndvi_name} saved.")
    cv2.destroyAllWindows()


'''
