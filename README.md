# QuadCam

> *Description to be filled in.*

The QuadCam system is a **stereo vision system for vegetation monitoring** that requires precise camera calibration, real-time processing, and hardware integration - making all these dependencies essential for the system to function properly as a complete multispectral imaging solution.

---

## Full Setup Guide

> Note: MacOS was used to implement this system, but the README is valid for all operating systems

### Components:
1) [Rasberry Pi 4 Model B](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/)
2) [OV9281 Monochrome Global Shutter Camera](https://docs.arducam.com/Raspberry-Pi-Camera/Native-camera/Global-Shutter/1MP-OV9281-OV9282/)
4) [Multi Camera HAT ](https://www.arducam.com/arducam-1mp4-quadrascopic-camera-bundle-kit-for-raspberry-pi-nvidia-jetson-nano-xavier-nx-four-ov9281-global-shutter-monochrome-camera-modules-and-camarray-camera-hat.html)

### Resources
1) [Setup Documentation](https://docs.arducam.com/Raspberry-Pi-Camera/Multi-Camera-CamArray/quick-start/#access-raspberry-pi-native-camera)
2) [Video Setup Tutorial](https://www.youtube.com/watch?v=jW4gcla1aOE)
3) [Kernel Driver](https://blog.arducam.com/faq/kernel-camera-driver/)

#### Further Reading
4) [Arducam MIPI monochrome global shutter cameras](https://forums.raspberrypi.com/viewtopic.php?t=267563)



### Repository Setup

---

## Step 1 – Flash Raspberry Pi OS to SD Card

1. Download and install [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2. Insert your micro-SD card using a card reader.
3. Open Raspberry Pi Imager and select:

   * **Device:** Raspberry Pi 4
   * **OS:** Raspberry Pi OS (64-bit) (Debian Bookworm)
   * **Storage:** Your SD card
4. When prompted with "Would you like to apply OS customisation settings?", click **Edit Settings** and configure the following:

#### 1. Set hostname
* **quadcam** 

#### 2. Set Username and Password

* [x] Enable "Set username and password"

  * **Username:** `av`
  * **Password:** `quadcam123`

#### 2. Enable SSH

* [x] Enable SSH

  * [x] Use password authentication

#### 3. Configure Wireless LAN *(skip if using Ethernet)*

* [x] Enable "Configure wireless LAN"

  * **SSID:** `YourNetworkName`
  * **Password:** `YourWiFiPassword`
  * **Country:** `AU`

#### 4. Set Locale Settings

* [x] Enable "Set locale settings"

  * **Time zone:** `Australia/Perth`
  * **Keyboard layout:** `us`


Click **Save**, then **Write** the image. Once complete, eject the SD card and insert it into your Raspberry Pi.

---

## Step 2 – First Boot and Basic Pi Setup

1. Insert the flashed SD card into the Pi and power it up.

2. Wait ≈ 45 seconds for the Pi to boot.
Run on PC to remove old key entry when re flashing.
```bash
ssh-keygen -R 192.168.0.157
```

3. On your laptop, find the Pi's IP address:

   ```
    ping quadcam.local
   ```

4. Connect via SSH:

Make sure SSH is enabled
On the Pi:

   ```bash
  sudo raspi-config
   ```
Go to: Interface Options → SSH → Enable

Exit and reboot:

   ```bash
  sudo reboot
   ```

then SSH
   ```
    # ssh <username>@quadcam.local
    ssh av@quadcam.local
    ssh av@192.168.0.157
   ```

sudo systemctl status ssh

you should see active (running)

if not:
sudo systemctl enable ssh
sudo systemctl start ssh

Run:

bash
hostname -I
eg 192.168.0.157

try pinging the laptop from the pi

on laptop:
```bash
ipconfig getifaddr en0
```
```bash
ping <laptop-ip>
```


### Recommended Workflow: 
> Remote Development via SSH + VS Code: 
> Use VS Code to open Pi remotely
- Install Visual Studio Code
- Install the Remote - SSH extension:
Extensions (⇧⌘X) → search "Remote - SSH" → Install
- Open Command Palette (⇧⌘P) → Remote-SSH: Connect to Host…
- Select your Pi IP (might need to add it to the config) 
- You'll be connected to your Pi and can edit code directly in the remote environment.

!Important
Clone the repository:

CMD + SHIFT + P
> File: Open Folder
> Open PI-AERIAL-PAYLOAD

```
mkdir -p ~/dev/pi-Aerial-Payload
cd ~/dev/pi-Aerial-Payload
git clone https://github.com/adriaan-vdb/pi-Aerial-Payload.git
cd pi-Aerial-Payload
```

### Link to the GITHUB repo for syncing
CMD+SHIFT+P 
> File: Open Folder
> PI-AERIAL-PAYLOAD

```bash
git remote remove origin
git remote add origin https://github.com/adriaan-vdb/pi-Aerial-Payload.git
```
#### To commit to github
```bash
git pull origin main
git add .
git commit -m "Updates on R-Pi"
git push origin main
```


## Step 3 - Run Configuration

Open the Raspberry Pi configuration utility:

```bash
sudo raspi-config
```

Navigate to the following options using the arrow keys and enable each:

- **Interface Options**
  - **Camera** → Enable
  - **I2C** → Enable *(required for QuadCam HAT EEPROM)*
  - **VNC** → Enable *(optional: for remote desktop access)*
  - **SSH** → Enable *(if not already enabled: allows terminal access)*
  - *(SPI can be left disabled unless used by other peripherals)*

After enabling, press `<Finish>` and reboot the Pi:

```bash
sudo reboot
```

> The QuadCam HAT uses the CSI-2 camera interface and I²C EEPROM, both of which must be enabled for correct operation.


---

## Step 4 – Update OS and Install Dependencies

### Update and upgrade the Pi:

```bash
sudo apt update && sudo apt full-upgrade -y
```

### Install required system packages:

```bash
sudo apt install -y git python3-pip libatlas-base-dev \
    libopenjp2-7 libtiff-dev libcap-dev \
    build-essential cmake pkg-config \
    python3-libcamera
```
---

## Step 5 – Install ArduCam QuadCam Driver

### Use libcamera to access the camera

> CHECK OS
```bash
uname -a
```

#### The following steps are for Raspberry Pi Bullseye OS 6.1.21 and Later/Bookworm OS

Step 1. Download the bash scripts
```bash
wget -O install_pivariety_pkgs.sh https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/install_script/install_pivariety_pkgs.sh
chmod +x install_pivariety_pkgs.sh
```

Step 2. Install libcamera
```bash
./install_pivariety_pkgs.sh -p libcamera_dev
```
Step 3. Install libcamera-apps
```bash
./install_pivariety_pkgs.sh -p libcamera_apps
```
Step 4. Modify .Config file

#### For Raspberry Pi Bookworm/Bullseye users running on Pi 4
```bash
sudo nano /boot/firmware/config.txt 
```
#### Find the line: [all], add the following item under it:
```bash
dtoverlay=arducam-pivariety
```
#### Modify the 1 to a 0 in
```bash
camera_auto_detect=0
```

### Save and reboot.

Step 5. Use libcamera to access Arducam Pivariety Camera
```bash
libcamera-still -t 5000
```
- Preview 5 seconds.
If you don't have a display screen, you can save an image without displaying it. And an image of test.jpg will be saved in the current directory.

```bash
libcamera-still -t 5000 -n -o test.jpg
```

---
### Troubleshooting

- **Camera Not Detected**:
  - Ensure the camera is properly connected.
  - Verify that the `dtoverlay` line is correctly added to the configuration file.
  - Check for the presence of `/dev/video0` using:
    ```bash
    ls /dev/video*
    ```
  - Check Available I2C Buses using:
    ```bash
    i2cdetect -l
    ```
- **Fix: Missing `arducam-pivariety_mono.json` Tuning File**
  - Run the following commands to install Arducam's custom version of `libcamera` and the necessary tuning files:
  ```bash
  sudo mkdir -p /usr/share/libcamera/ipa/rpi/vc4/

  wget -O install_pivariety_pkgs.sh https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/install_script/install_pivariety_pkgs.sh
  chmod +x install_pivariety_pkgs.sh
  ./install_pivariety_pkgs.sh -p libcamera_dev
  ./install_pivariety_pkgs.sh -p libcamera_apps
  ```
  - Then verify the tuning file is present:
  ```bash
  ls /usr/share/libcamera/ipa/rpi/vc4/arducam-pivariety_mono.json
  ```




---

## Step 6 – Verify Camera Installation and Basic Testing

### Check I2C Communication with the Arducam HAT

The Arducam CamArray HAT communicates over I²C to handle camera switching. You can verify it’s detected by scanning for its address (`0x24`) on available I²C buses:

```bash
for i in {0..22}; do echo "Bus $i"; sudo i2cdetect -y $i | grep 24 && echo "  ✅ Found 0x24" || echo "  ❌ Not on this bus"; done
```

> The device should be visible on one or more buses (commonly bus 20 or 21). Seeing `0x24` confirms that the HAT is connected and responding.

### Link the missing arducam-pivariety_mono.json file 
```bash
sudo ln -s ov9281_mono.json arducam-pivariety_mono.json
```
> This creates a symbolic link that tells libcamera to use the ov9281_mono.json tuning file whenever it looks for arducam-pivariety_mono.json.

### Capture a Test Image with libcamera

Use `libcamera-still` to test image capture from the camera stack:

```bash
libcamera-still -t 5000 -n -o test.jpg
```

> This will capture a 4-camera composite image (typically 5120×800 pixels) and save it as `test.jpg`. If the image is saved without errors, your camera pipeline is working correctly.

---

## Step 7 – Python Environment Setup and Initial Capture


### Install Python libraries:

1. Install virtualenv tools if not present
```bash
sudo apt install -y python3-venv python3-full
```
2. Create a virtual environment with system site packages access (in your project dir)
```bash
cd ~/Documents/pi-Aerial-Payload
rm -rf venv
python3 -m venv venv --system-site-packages
```
> **Note**: The `--system-site-packages` flag is required to access the system `libcamera` libraries that picamera2 depends on.

3. Activate it
```bash
source venv/bin/activate
```
4. Upgrade pip
```bash
pip install --upgrade pip
```
5. Install your project dependencies
```bash
pip install "opencv-python==4.5.5.64" "picamera2==0.3.18" "RPi.GPIO==0.7.1a4" numpy matplotlib flask
```

To exit the venv, run:

```bash
deactivate
```

> These versions match those used in the original thesis implementation.

### To activate Your Virtual Environment

```bash
# Navigate to project directory
cd ~/Documents/pi-Aerial-Payload

# Activate virtual environment
source venv/bin/activate
```

### Simple Headless Camera Test

Run the simple headless camera test script that doesn't require VNC or GUI:

```bash
cd RPi_Code

# Run simple camera test (captures 3 test images)
python3 simple_camera_test.py
```

> **Note**: This headless script captures 3 test images without requiring a display. Images are saved in a timestamped directory (e.g., `camera_test_20241213_143022/`). Expected image size is 2560x400 pixels (4 cameras combined).

---

## Step 8 – VNC Configuration (Optional but Recommended)

VNC is required for live preview and calibration GUIs.

### Enable VNC on Pi

```bash
sudo raspi-config
# Navigate to: Interface Options → VNC → Enable
sudo reboot
```

### Connect from Your Laptop

1. Install [RealVNC Viewer](https://www.realvnc.com/en/connect/download/viewer/)
2. Connect to `quadcam.local` or your Pi's IP address
3. Use your Pi credentials (`av` / `quadcam123`)

```bash
export QT_QPA_PLATFORM=vnc
DISPLAY=:0
```
#### To check VNC is running correctly
```bash
ps aux | grep vnc | grep -v grep
```

### Live Preview Solutions

#### Option 1: Web-Based Live Preview (Recommended - Works without VNC)
```bash
# Navigate to RPi_Code directory and activate virtual environment
cd ~/Documents/pi-Aerial-Payload/RPi_Code
source ../venv/bin/activate

# Start the web-based live preview server
python3 WebLivePreview.py
```

The following script allows for individual brightness adjustment
```bash
python3 WebLivePreview_Enhanced.py
```

Then open your web browser and go to:
- **From your Phone:** `http://192.168.0.157:5000` (or your Pi's IP address)
- **From the Pi locally:** `http://localhost:5000`
- **From your computer:** `http://127.0.0.1:5000/`

**To find your Pi's IP address:**
```bash
hostname -I
```

#### Option 2: OpenCV GUI Live Preview (Requires VNC to view from laptop)
> This option has less latency but can't be viewed from a mobile device
```bash
# Set proper display environment and run OpenCV preview
export DISPLAY=:0
export QT_QPA_PLATFORM=xcb
chmod 700 /run/user/1000
python3 LivePreview.py
```

**Controls:**
- **'c'** - Capture preview resolution image (1280x200)
- **'q'** - Quit application  
- **'f'** - Toggle fullscreen mode
- **'ESC'** - Exit fullscreen mode


---

## Step 9 – Stereo Calibration (Required for Stereo Vision)

### Prepare Calibration Images

1. **Print a checkerboard pattern** (recommended: 9×6 squares, 25mm each)
2. **Capture calibration images** by pointing all cameras at the checkerboard from different angles and distances
3. **Ensure good coverage** - capture at least 10-15 image sets

### Create Calibration Directory Structure

```bash
# Create directories for calibration images
mkdir -p ~/Documents/pi-Aerial-Payload/calibration_images/raw
mkdir -p ~/Documents/pi-Aerial-Payload/calibration_images/split
mkdir -p ~/Documents/pi-Aerial-Payload/maps
```

### Capture Calibration Images

```bash
cd RPi_Code

# Capture multiple sets of calibration images
python3 Capture_V3.py
```

### Split Calibration Images

```bash
python3 Split_V3.py
```

### Run Stereo Calibration

```bash
python3 Stereo_V4.py
```

> This generates stereo rectification maps saved as XML files in the `maps/` directory.

---

## Step 10 – Live Preview and Real-time Processing

### Configure Live Calibration Paths

Edit `LiveCal_V4.py` to update the hardcoded paths:

```bash
nano LiveCal_V4.py
```

Update the paths in the script to match your directory structure:
```python
# Update these paths
cv_file.open('/home/av/Documents/pi-Aerial-Payload/maps/stereoMap_03.xml', cv2.FileStorage_READ)
cvFile1.open('/home/av/Documents/pi-Aerial-Payload/maps/stereoMap_12.xml', cv2.FileStorage_READ)
```

### Run Live Preview

```bash
python3 LiveCal_V4.py
```

**Controls:**
- **'c'** - Capture calibrated frame
- **'q'** - Quit application

> **Note**: Requires VNC connection for GUI display. The live preview shows rectified stereo pairs.

---

## Step 11 – Post-Processing and Vegetation Index Generation

### Post-Process Captured Images

```bash
python3 PostProc_V2.py
```

### Generate Vegetation Indices

```bash
python3 VIGen.py
```

> This generates NDVI (Normalized Difference Vegetation Index) from the captured multispectral images.

---

## Step 12 – GPIO Remote Trigger (Optional)

For drone integration, use the GPIO trigger script:

```bash
python3 DroneGPIO.py
```

> This script listens for GPIO signals from a flight controller and triggers synchronized captures.

---

## Updated File Structure

```
pi-Aerial-Payload/
├── README.md
├── RPi_Code/
│   ├── simple_camera_test.py  # Headless camera test script
│   ├── WebLivePreview.py      # Web-based live preview (recommended)
│   ├── LivePreview.py         # OpenCV GUI live preview (requires VNC)
│   ├── Capture_V3.py          # Main capture script (batch mode)
│   ├── Split_V3.py            # Image splitting utility
│   ├── Stereo_V4.py           # Stereo calibration
│   ├── LiveCal_V4.py          # Live preview and calibration
│   ├── PostProc_V2.py         # Post-processing
│   ├── VIGen.py               # Vegetation index generation
│   └── DroneGPIO.py           # GPIO trigger integration
├── captures/
│   ├── split/                 # Individual camera images
│   ├── live_preview/          # OpenCV live preview captures
│   └── web_preview/           # Web preview captures
├── calibration_images/
│   ├── raw/                   # Raw combined images
│   └── split/                 # Individual camera images
├── maps/                      # Stereo calibration maps
├── results/                   # Processed outputs
├── venv/                      # Python virtual environment
├── rpicam-apps_1.7.0-2_arm64.deb
├── libcamera*.deb             # Camera library packages
└── install_pivariety_pkgs.sh  # Driver installation script
```

---

## Important Notes

### Path Configuration
- **All Python scripts contain hardcoded paths** that need to be updated for your specific setup
- **Before running any script**, edit the file paths to match your directory structure
- **Common paths to update**:
  - `/home/a22498729/Desktop/` → `/home/av/Documents/pi-Aerial-Payload/`
  - Calibration image directories
  - Output directories

### Workflow Summary
1. **Test** → Use `simple_camera_test.py` for headless camera testing
2. **Live Preview** → Use `WebLivePreview.py` for real-time viewing and capture (recommended)
3. **Batch Capture** → Use `Capture_V3.py` for automated image acquisition
4. **Split** → Use `Split_V3.py` to separate camera feeds  
5. **Calibrate** → Use `Stereo_V4.py` for stereo calibration
6. **Live Processing** → Use `LiveCal_V4.py` for real-time stereo processing
7. **Post-Process** → Use `PostProc_V2.py` and `VIGen.py` for analysis

### Troubleshooting
- **Camera not found**: Check `/dev/video*` devices exist
- **GUI not displaying**: Use `simple_camera_test.py` for headless testing, or ensure VNC is enabled and connected
- **Path errors**: Update hardcoded paths in Python scripts
- **Calibration fails**: Ensure adequate checkerboard images with good coverage
- **SSH issues**: Make sure your privacy and security settings allow network access so you can ssh into the R-Pi from the terminal (can be auto blocked on macOS)
---

## Dependency Explanations

This section explains why each dependency is required for the QuadCam stereo vision system for vegetation monitoring.

### System Package Dependencies

#### Essential for Core Functionality
- **`git`** - Required for cloning the repository and version control
- **`python3-pip`** - Package installer for Python libraries
- **`python3-venv`** & **`python3-full`** - Virtual environment support for isolated Python dependencies

#### OpenCV Dependencies
- **`libatlas-base-dev`** - Linear algebra library that OpenCV uses for optimized mathematical operations (matrix operations, image processing)
- **`libopenjp2-7`** - JPEG 2000 codec support for OpenCV image reading/writing
- **`libtiff-dev`** - TIFF image format support for OpenCV
- **`build-essential`** - Contains GCC compiler and build tools needed to compile OpenCV from source
- **`cmake`** - Build system for compiling OpenCV extensions
- **`pkg-config`** - Helps find library dependencies during compilation

#### Hardware Interface
- **`libcap-dev`** - Required for camera capture permissions and low-level camera access

### Python Library Dependencies

#### Core Image Processing
- **`opencv-python==4.5.5.64`** - Used extensively in:
  - `Stereo_V4.py` - Stereo camera calibration, chessboard detection, image rectification
  - `LiveCal_V4.py` - Real-time stereo mapping and camera feed processing
  - `PostProc_V2.py` - NDVI calculation and image post-processing
  - `Split_V3.py` - Image splitting and manipulation
  - `VIGen.py` - Vegetation index generation and color mapping

#### Camera Control
- **`picamera2==0.3.18`** - Used in:
  - `Capture_V3.py` - Main camera capture functionality
  - `DroneGPIO.py` - GPIO-triggered camera capture
  - `LiveCal_V4.py` - Camera interface integration

#### Hardware Control
- **`RPi.GPIO==0.7.1a4`** - Used in:
  - `DroneGPIO.py` - GPIO pin control for drone trigger integration

#### Mathematical Operations
- **`numpy`** - Used in:
  - `Stereo_V4.py` - Matrix operations for camera calibration
  - `PostProc_V2.py` - NDVI calculations and image array processing
  - `Split_V3.py` - Image array manipulation
  - `VIGen.py` - Numerical operations for vegetation indices

#### Visualization
- **`matplotlib`** - Used in:
  - `Stereo_V4.py` - Plotting calibration results and stereo pair comparisons

#### Web Interface
- **`flask`** - Used in:
  - `WebLivePreview.py` - Web-based live camera preview and capture interface

  ---

## Credits

This project build on the initial work of **Hannah Page** as part of her **GENG5512 Engineering Research Project (Multispectral Imaging Drone Payload)**.

