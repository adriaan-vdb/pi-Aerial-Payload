import cv2
import glob
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams.update({'font.size': 20})
import time
# Code Modified from [put github ref here] and [other ref here]
#
#
#
startTime = time.time()
PATTERN_SIZE = (5, 3) #bigger box is 10, 7
def StereoMap(im1, im2):
    #load the images in and ensure there are the same number of each side. 
    left_imgs = list(sorted(glob.glob(f'/home/a22498729/Desktop/Picam/Batch2/Split/*{im1}.png'))) #nir 
    right_imgs = list(sorted(glob.glob(f'/home/a22498729/Desktop/Picam/Batch2/Split/*{im2}.png')))#red
    assert len(left_imgs) == len(right_imgs)
    print(len(left_imgs))

    #set up the criteria + arrays for identifying the points in the real world + their corresponding points in the image
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3)
    img_size = None
    pattern_points = np.zeros((np.prod(PATTERN_SIZE), 3), np.float32)
    pattern_points[:, :2] = np.indices(PATTERN_SIZE).T.reshape(-1, 2)
    pattern_points = pattern_points * len(left_imgs)
    left_pts, right_pts, objpoints = [], [] , []

    count = 0
    usedImg = 0
    for left_img_path, right_img_path in zip(left_imgs, right_imgs):
        #read the two images one at a time
        left_img = cv2.imread(left_img_path, cv2.IMREAD_GRAYSCALE)
        right_img = cv2.imread(right_img_path, cv2.IMREAD_GRAYSCALE)
        img_size = (left_img.shape[1], left_img.shape[0])
        
        #find the chessboard corners in each image
        res_left, corners_left = cv2.findChessboardCorners(left_img, PATTERN_SIZE)
        res_right, corners_right = cv2.findChessboardCorners(right_img, PATTERN_SIZE)
        print("file count:" ,count)
        count = count+1 #the number of images checked 

        #check whether the chessboard was found
        if res_left and res_right== True:
            usedImg = usedImg +1
            print("count of files used for calibration:", usedImg)
            objpoints.append(pattern_points)
            corners_left = cv2.cornerSubPix(left_img, corners_left, (10, 10), (-1,-1), criteria)
            corners_right = cv2.cornerSubPix(right_img, corners_right, (10, 10), (-1,-1), criteria)
            left_pts.append(corners_left)
            right_pts.append(corners_right)
            #if calibration isnt working, use below code to check what is being recognized by the code
            '''cv2.drawChessboardCorners(left_img, PATTERN_SIZE, corners_left, res_left)
            cv2.imshow('img left', left_img)
            cv2.drawChessboardCorners(right_img, PATTERN_SIZE, corners_left, res_right)
            cv2.imshow('img right', right_img)
            cv2.waitKey(0)
    cv2.destroyAllWindows()'''
    #takes the above parameters and produces the rotational/translation/distortion matrix between the two cameras
    err, Kl, Dl, Kr, Dr, R, T, E, F = cv2.stereoCalibrate(objpoints, left_pts, right_pts, None, None, None, None, img_size, flags=0)
    #also just to print the required parameters to check
    ''''print('Left camera:')
    print(Kl)
    print('Left camera distortion:')
    print(Dl)
    print('Right camera:')
    print(Kr)
    print('Right camera distortion:')
    print(Dr)
    print('Rotation matrix:')
    print(R)
    print('Translation:')
    print(T)'''
    print(err)
    folder = f"/home/a22498729/Desktop/Working/Maps/stereoMap_{im1}{im2}.xml"
    #creates Undistortion map that can be used 
    R1, R2, P1, P2, Q, validRoi1, validRoi2 = cv2.stereoRectify(Kl, Dl, Kr, Dr, img_size, R, T)
    xmap1, ymap1 = cv2.initUndistortRectifyMap(Kl, Dl, R1, P1, img_size, cv2.CV_32FC1)
    xmap2, ymap2 = cv2.initUndistortRectifyMap(Kr, Dr, R2, P2, img_size, cv2.CV_32FC1)

    #saves the maps as an XML file read by the other functions in live calibration. 
    cv_file = cv2.FileStorage(folder, cv2.FILE_STORAGE_WRITE)
    cv_file.write('stereoMap1_x',xmap1)
    cv_file.write('stereoMap1_y',ymap1)
    cv_file.write('stereoMap2_x',xmap2)
    cv_file.write('stereoMap2_y',ymap2)
    cv_file.write('Roi1',validRoi1)
    cv_file.write('Roi2',validRoi2)
    cv_file.release()
    return xmap1, ymap1, xmap2, ymap2

def testCalibration(xmap1, ymap1, xmap2, ymap2,im1, im2):
    #test calibration to check whether the image is ok 
    left_img = cv2.imread(f'/home/a22498729/Desktop/Picam/Split/im0_{im1}.png')
    right_img = cv2.imread(f'/home/a22498729/Desktop/Picam/Split/im0_{im2}.png')

    left_img_rectified = cv2.remap(left_img, xmap1, ymap1, cv2.INTER_LINEAR)
    right_img_rectified = cv2.remap(right_img, xmap2, ymap2, cv2.INTER_LINEAR)
    plt.figure(0, figsize=(12,10))
    plt.subplot(221)
    plt.title('left original')
    plt.imshow(left_img, cmap='gray')
    plt.subplot(222)
    plt.title('right original')
    plt.imshow(right_img, cmap='gray')
    plt.subplot(223)
    plt.title('left rectified')
    plt.imshow(left_img_rectified, cmap='gray')
    plt.subplot(224)
    plt.title('right rectified')
    plt.imshow(right_img_rectified, cmap='gray')
    plt.tight_layout()
    plt.savefig(f'plot{im1,im2}.png',dpi=300,bbox_inches='tight')
    plt.show()

xmap0, ymap0, xmap3, ymap3 = StereoMap(0,3)
print('map_1_done')
testCalibration(xmap0, ymap0, xmap3, ymap3, 0,3)
xmap1, ymap1, xmap2, ymap2 =StereoMap(1,2)
print('map_2_done')
print("total time:", (time.time()- startTime))
testCalibration(xmap1, ymap1, xmap2, ymap2,1,2)