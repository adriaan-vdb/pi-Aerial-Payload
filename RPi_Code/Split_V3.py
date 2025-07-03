#Code needs to take the image, split it into 4 images 
#then it needs to do the image registration/calibration 
import cv2
import numpy as np
import time
import glob
import os
#from fastiecm import fastiecm
#from picamera2 import Picamera2, Preview
from PIL import Image
from datetime import datetime

#splits the image into 4 frames
#define folders 
originalFolder = "/home/a22498729/Desktop/Picam/Batch2"
images =glob.glob(originalFolder+'/*.png')
lowContrast = glob.glob("A2/*.png")
#print(lowContrast)
#print(images)

def split(image,image_name):
    image = np.array(image,dtype=float)/float(255)
    shape = image.shape
    #print(shape)
    h = int(shape[0])
    w = int(shape[1])
    
    img0 = image[0:h,0:w//4]
    img1 = image[0:h,w//4:w//2]
    img2 = image[0:h,w//2:3*w//4]
    img3 = image[0:h,3*w//4:w]
    #print(img0.shape)
    '''
        for i in range(4):
        img = locals()["img" +str(i)]
        timestamp = datetime.now().strftime("%H-%M-%S")
        filename = f"{timestamp}"
        #cv2.imshow(filename,img)
        folder = f"A{i}"
        #cv2.waitKey(0)
        filepath = os.path.join(folder, filename + '.png')
        cv2.imwrite(filepath,255*img) #multiply by 255 to get the pixel values back to where the cv2.imwrite can recognize them,,
    print(img0.shape)  
    #cv2.destroyAllWindows()
    '''

    return img0, img1, img2 , img3

def contrast(im):
    #im = np.array(im,dtype=float)/float(255) 
    in_min = np.percentile(im,25)
    in_max = np.percentile(im,95)
    out_min = 0.0
    out_max = 255.0
    out = im - in_min
    out *= ((out_min - out_max)/(in_min - in_max))
    out += in_min
    superContrast = np.clip(out, 0, 255).astype(np.uint8)
    return out 

for index, image in enumerate(images):
    img = cv2.imread(image)
    img0, img1, img2, img3 =split(img, 'split')
    #img2 = contrast(img2)
    #img0 = contrast(img0)
    for i in range(4):
        img = locals()["img" +str(i)]
        #timestamp = datetime.now().strftime("%H-%M-%S")
        filename = f"im{index}_{i}"
        #cv2.imshow(filename,img)
        directoryPath =  f"/home/a22498729/Desktop/Picam/Batch2/Split"
        if not os.path.exists(directoryPath):
            os.makedirs(directoryPath)
        #cv2.waitKey(0)
        filepath = os.path.join(directoryPath, filename + '.png')
        cv2.imwrite(filepath,255*img) #multiply by 255 to get the pixel values back to where the cv2.imwrite can recognize them,,
        #print(img.shape)  
    #cv2.destroyAllWindows()
