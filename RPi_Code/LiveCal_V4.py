#imports
import time
startTime = time.time() 
import cv2
from Split_V3 import split
from datetime import datetime
import os
from LiveNDVI import TotalNDVI
#main function

#opening and saving the parameters from the first stereomap:
cv_file = cv2.FileStorage()
cv_file.open('/home/av/Documents/pi-Aerial-Payload/maps/stereoMap_03.xml', cv2.FileStorage_READ) #contains frame 0 and 3 
stereoMap0_x = cv_file.getNode('stereoMap1_x').mat() #frame 0
stereoMap0_y = cv_file.getNode('stereoMap1_y').mat() 
stereoMap3_x = cv_file.getNode('stereoMap2_x').mat() #frame 1
stereoMap3_y = cv_file.getNode('stereoMap2_y').mat()
#get the range of interest from the file, and scale it so it can be used to crop the live image
roi0 = ((cv_file.getNode('Roi1').mat())+30)/2 #+30 works for some reason
roi3 = (cv_file.getNode('Roi2').mat())/2

flatRoi0 = roi0.flatten()
left0,top0,right0,bottom0 = [int(value) for value in flatRoi0]
flatRoi3 = roi3.flatten()
left3,top3,right3,bottom3 = [int(value) for value in flatRoi3]

cvFile1 = cv2.FileStorage()
cvFile1.open('/home/av/Documents/pi-Aerial-Payload/maps/stereoMap_12.xml', cv2.FileStorage_READ) #contains frame 1 and 2
stereoMap1_x = cvFile1.getNode('stereoMap1_x').mat() #frame 1
stereoMap1_y = cvFile1.getNode('stereoMap1_y').mat() 
stereoMap2_x = cvFile1.getNode('stereoMap2_x').mat() #frame 2
stereoMap2_y = cvFile1.getNode('stereoMap2_y').mat()
#get the range of interest from the file, and scale it so it can be used to crop the live image
roi1 = ((cvFile1.getNode('Roi1').mat()))/2
roi2 = (cvFile1.getNode('Roi2').mat())/2
flatRoi1 = roi1.flatten()
left1,top1,right1,bottom1 = [int(value) for value in flatRoi1]

flatRoi2 = roi2.flatten()
left2,top2,right2,bottom2 = [int(value) for value in flatRoi2]
#print(top3,bottom3,left3,right3)
#print(top0,bottom0,left0,right0)
#print(flatRoi0,flatRoi3,flatRoi1,flatRoi2)

# Updated paths to use correct user directory
folder_0 = "/home/av/Documents/pi-Aerial-Payload/results"
folder_1 = "/home/av/Documents/pi-Aerial-Payload/results/raw"

# Ensure result directories exist
os.makedirs(folder_0, exist_ok=True)
os.makedirs(folder_1, exist_ok=True)

cap = cv2.VideoCapture(0,cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,2560)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,400)
#writer =cv2.VideoWriter('test.avi', cv2.VideoWriter_fourcc('m','p','4','v'),20,(2560,400))

image_count = 0
#starts camera
print("init time:", (time.time()- startTime))
while(cap.isOpened()):
    ret, frame =cap.read()
    #check if the camera is open
    if ret == False:
       print("failed to open")
       break
    #resizes the live feed to fit in screen
    cv2.namedWindow("Live Feed",cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Live Feed", 1280,200)
    cv2.imshow("Live Feed",frame) 
    #uses prev. created function to split the frames into 4 parts 
    img0, img1, img2 ,img3= split(frame,"live")

    frame_0 = cv2.remap(img0, stereoMap0_x, stereoMap0_y, cv2.INTER_LINEAR)
    frame_1 = cv2.remap(img1, stereoMap1_x, stereoMap1_y, cv2.INTER_LINEAR)
    frame_2 = cv2.remap(img2, stereoMap2_x, stereoMap2_y, cv2.INTER_LINEAR)
    frame_3 = cv2.remap(img3, stereoMap3_x, stereoMap3_y, cv2.INTER_LINEAR)
    
    crop0 = frame_0[top0+5:bottom0-37,left0+7:right0+3]  #height width
    crop3 = frame_3[top3+35:bottom3+5,left3+3:right3-13] 

    crop1 = frame_1[top1:bottom1+5,left1:right1-17]
    crop2 = frame_2[top2:bottom2,left2+10:right2]

    '''
    crop0 = frame_0[top0:bottom0,left0:right0]  #height width
    crop1 = frame_1[top1:bottom1,left1:right1]
    crop2 = frame_2[top2:bottom2,left2:right2]
    crop3 = frame_3[top3:bottom3,left3:right3] 
       crop1 = frame_1[top1:bottom1+6,left1:right1-17]
    crop2 = frame_2[top2:bottom2-5,left2+10:right2]
    #trial and error from eye
    '''
    #Lcrop = frame_0[top+5:bottom-40,left0+5:right+5]
    #Rcrop = frame_1[top1+35:bottom1+5,left1+5:right1-15]
    #cv2.imshow("frame 1",frame_1)
    #cv2.imshow("frame 2",frame_2)
    cv2.imshow("frame 0",crop0)
    #cv2.imshow("cropped 1",crop1)
    #cv2.imshow("cropped 2",crop2)
    cv2.imshow("frame 3",crop3)    
    

    timestamp = datetime.now().strftime("%d_%H-%M-%S")

    key = cv2.waitKey(1)
    
    if key == ord('q'):  # Press 'q' to quit
        print(flatRoi0,flatRoi3,flatRoi1,flatRoi2)
        print("0",crop0.shape,"3",crop3.shape,"1",crop1.shape,"2",crop2.shape)
        break
    elif key == ord('c'):  # Press 'c' to capture image
        # Note: TotalNDVI function from LiveNDVI module may need path updates too
        try:
            TotalNDVI(crop0, crop3,image_count) #red then NIR. Need to fix this code to work with frame input
            TotalNDVI(crop1, crop2,image_count)
        except Exception as e:
            print(f"NDVI processing error: {e}")
            
        filename0 = f"{timestamp}im{image_count}frame0"
        filename1 = f"{timestamp}im{image_count}frame1"
        filename2 = f"{timestamp}im{image_count}frame2"
        filename3 = f"{timestamp}im{image_count}frame3"
        filename4 = f"{timestamp}im{image_count}"
        filepath_0= os.path.join(folder_0, filename0 + '.png')
        filepath_1= os.path.join(folder_0, filename1 + '.png') 
        filepath_2= os.path.join(folder_0, filename2 + '.png')  
        filepath_3= os.path.join(folder_0, filename3 + '.png')
        filepath_4= os.path.join(folder_1, filename4 + '.png')
        print(f"Capturing image {image_count}")
        cv2.imwrite(filepath_0,255*crop0) #multiply by 255 to get the pixel values back to where the cv2.imwrite can recognize them,,
        cv2.imwrite(filepath_1,255*crop1)
        cv2.imwrite(filepath_2,255*crop2) #multiply by 255 to get the pixel values back to where the cv2.imwrite can recognize them,,
        cv2.imwrite(filepath_3,255*crop3)
        #cv2.imwrite(filepath_2,255*frame_2) #multiply by 255 to get the pixel values back to where the cv2.imwrite can recognize them,,
        #cv2.imwrite(filepath_3,255*frame_3) #multiply by 255 to get the pixel values back to where the cv2.imwrite can recognize them,,
        cv2.imwrite(filepath_4,frame) #the raw data 

        image_count += 1
        if image_count >= 5:
            print("All images captured")
            break
    
    #print("image taken")    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()



