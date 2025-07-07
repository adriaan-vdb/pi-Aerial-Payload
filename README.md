# QuadCam

> *Description to be filled in.*

---

## Full Setup Guide

### Components:
1) [Rasberry Pi 4 Model B](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/)
2) [OV9281 Monochrome Global Shutter Camera](https://docs.arducam.com/Raspberry-Pi-Camera/Native-camera/Global-Shutter/1MP-OV9281-OV9282/)
4) [Multi Camera HAT ](https://www.arducam.com/arducam-1mp4-quadrascopic-camera-bundle-kit-for-raspberry-pi-nvidia-jetson-nano-xavier-nx-four-ov9281-global-shutter-monochrome-camera-modules-and-camarray-camera-hat.html)

### Resources
1) [Setup Documentation](https://docs.arducam.com/Raspberry-Pi-Camera/Multi-Camera-CamArray/quick-start/#access-raspberry-pi-native-camera)
2) [Video Setup Tutorial](https://www.youtube.com/watch?v=jW4gcla1aOE)

### Troubleshooting tips

- Make sure your privacy and security settings allow network access so you can ssh into the R-Pi from the terminal (can be auto blocked on macOS)


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
git remote add origin <>
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

Update and upgrade the Pi:

```
sudo apt update && sudo apt full-upgrade -y
```

Install required system packages:

```
sudo apt update
sudo apt install -y git python3-pip libatlas-base-dev \
    libopenjp2-7 libtiff-dev \
    build-essential cmake pkg-config
```

Install Python libraries:

1. Install virtualenv tools if not present
sudo apt install -y python3-venv python3-full

2. Create a virtual environment (in your project dir)
python3 -m venv venv

3. Activate it
source venv/bin/activate

4. Upgrade pip
pip install --upgrade pip

5. Install your project dependencies
```bash
pip install "opencv-python==4.5.5.64" "RPi.GPIO==0.7.1a4" numpy matplotlib
```

To exit the venv, run:

```bash
deactivate
```

> These versions match those used in the original thesis implementation.

---

## Step 5 – Install ArduCam QuadCam Driver

For Raspberry Pi Bookworm OS on Pi4, so the following:

### Edit the config
sudo nano /boot/firmware/config.txt 
#Find the line: camera_auto_detect=1, update it to:
camera_auto_detect=0
#Find the line: [all], add the following item under it:
dtoverlay=ov9281
#Save and reboot.

### Use libcamera to access the camera
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
Step 4. Preview the camera
```bash
libcamera-still -t 0
```

---

```
git clone https://github.com/ArduCAM/RaspberryPi.git ~/arducam_setup
cd ~/arducam_setup/Multi_Camera_Adapter/Multi_Adapter_Board_4Channel/Legacy/Multi_Camera_Adapter_V2.1_python/
chmod +x init_camera.sh
sudo ./init_camera.shsudo nano /boot/firmware/config.txt 

# Optional: test with adapter preview
python3 previewOpencv.py
```

After reboot, verify the camera stack:

```
dmesg | grep camarray
libcamera-hello -t 2000
```

> If the camera stack is not detected, rerun the setup script.

---

## Step 6 – Smoke Test and Live Preview

### Basic Capture Test

```
python3 Capture_V3.py
python3 Split_V3.py
```

> Outputs appear in `QuadCam/raw/` and `QuadCam/split/`. Expect four monochrome images.

### Live Preview

```
python3 LiveCal_V3.py
```

* Press **Space** to capture a synchronised frame.
* Requires VNC for GUI-based live viewing.

---

## VNC Configuration (Optional)

### Enable VNC on Pi

```
sudo raspi-config
# Interface Options → VNC → Enable
sudo reboot
```

### On Your Laptop

1. Install [RealVNC Viewer](https://www.realvnc.com/en/connect/download/viewer/).
2. Open VNC Viewer and connect to `quadcam.local`.
3. Log in using your Pi credentials.

---

## Step 7 – Calibration *(one-time per unit or lens set)*

Run stereo calibration using a 9 × 6 checkerboard (25 mm square size):

```
python3 Stereo_V4.py --rows 6 --cols 9 --square 25
```

> This generates stereo rectification maps saved under `maps/`.

---

## Step87 – Post-Processing and Index Generation

Run post-processing on raw captures:

```
python3 PostProc_V2.py --in raw/ --map maps/ --out calibrated/
```

Generate NDVI or PRI:

```
python3 VIGen.py \
    --nir calibrated/850 \
    --red calibrated/660 \
    --out indices/ndvi.png
```

---

## Step 9 – GPIO Remote Trigger *(Optional)*

Run this to listen for GPIO pin 14 triggers (e.g. from a flight controller):

```
python3 DroneGPIO.py --pin 14 --save flight_captures/
```

> Captures are synchronised on each **HIGH** signal to GPIO 14.

---

## File Structure *(to be completed)*

```
QuadCam/
├── 01. Matlab Code/
├── 02. CAD Files/
├── 03. RPi Code/
│   ├── Capture_V3.py
│   ├── DroneGPIO.py
│   ├── LiveCal_V3.py
│   ├── PostProc_V2.py
│   ├── Split_V3.py
│   ├── Stereo_V4.py
│   └── VIGen.py
├── raw/
├── split/
├── calibrated/
├── maps/
├── indices/
└── README.md
```

---

## Credits

Initial development by **Hannah Page** as part of the **GENG5512 Engineering Research Project (Multispectral Imaging Drone Payload)**.


# pi-Aerial-Payload

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

### Why These Specific Versions Matter

The specific versions (`opencv-python==4.5.5.64`, `picamera2==0.3.18`, `RPi.GPIO==0.7.1a4`) are locked to match the original thesis implementation, ensuring:
- **Compatibility** - Known working configuration
- **Reproducibility** - Same results as original research
- **Stability** - Avoiding breaking changes in newer versions

### Project Overview

The QuadCam system is a **stereo vision system for vegetation monitoring** that requires precise camera calibration, real-time processing, and hardware integration - making all these dependencies essential for the system to function properly as a complete multispectral imaging solution.
