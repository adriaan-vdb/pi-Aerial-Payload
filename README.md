+++markdown

# QuadCam

> *Description to be filled in.*

---

## Full Setup Guide

### Troubleshooting tips

- The terminal in side of VS code can be blocked by an unknown firewall (try the native terminal)


### Repository Setup

Clone the repository:

```
git clone <your-repo-url>
cd QuadCam
```

---

## Step 1 – Flash Raspberry Pi OS to SD Card

1. Download and install [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2. Insert your micro-SD card using a card reader.
3. Open Raspberry Pi Imager and select:

   * **Device:** Raspberry Pi 4
   * **OS:** Raspberry Pi OS (64-bit) (Debian Bookworm)
   * **Storage:** Your SD card
4. When prompted with **“Would you like to apply OS customisation settings?”**, click **Edit Settings** and configure the following:

#### 1. Set hostname
* **quadcam** 

#### 2. Set Username and Password

* [x] Enable “Set username and password”

  * **Username:** `av`
  * **Password:** `quadcam123`

#### 2. Enable SSH

* [x] Enable SSH

  * [x] Use password authentication

#### 3. Configure Wireless LAN *(skip if using Ethernet)*

* [x] Enable “Configure wireless LAN”

  * **SSID:** `YourNetworkName`
  * **Password:** `YourWiFiPassword`
  * **Country:** `AU`

#### 4. Set Locale Settings

* [x] Enable “Set locale settings”

  * **Time zone:** `Australia/Perth`
  * **Keyboard layout:** `us`



Click **Save**, then **Write** the image. Once complete, eject the SD card and insert it into your Raspberry Pi.

---

## Step 2 – First Boot and Basic Pi Setup

1. Insert the flashed SD card into the Pi and power it up.

2. Wait ≈ 45 seconds for the Pi to boot.

3. On your laptop, find the Pi’s IP address:

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



5. Run configuration:

   ```
    sudo raspi-config
    # Interface Options → Enable Camera
    # Interface Options → Enable I2C
    # Interface Options → Enable VNC (optional)
    sudo reboot
   ```

> The QuadCam HAT uses the CSI-2 camera interface and I²C EEPROM.

---

## Step 3 – Update OS and Install Dependencies

Update and upgrade the Pi:

```
sudo apt update && sudo apt full-upgrade -y
```

Install required system packages:

```
sudo apt install -y git python3-pip libatlas-base-dev \
    libopenjp2-7 libtiff5 libcamera-utils build-essential cmake pkg-config
```

Install Python libraries:

```
python3 -m pip install --upgrade pip
pip install "opencv-python==4.6.0" "picamera2==0.3.18" \
    "RPi.GPIO==0.7.1a4" numpy matplotlib
```

> These versions match those used in the original thesis implementation.

---

## Step 4 – Install ArduCam QuadCam Driver

```
git clone https://github.com/ArduCAM/Arducam-Pi-Setup.git ~/arducam_setup
cd ~/arducam_setup
chmod +x arducamsetup.sh
sudo ./arducamsetup.sh
```

After reboot, verify the camera stack:

```
dmesg | grep camarray
libcamera-hello -t 2000
```

> If the camera stack is not detected, rerun the setup script.

---

## Step 5 – Smoke Test and Live Preview

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

## Step 6 – Calibration *(one-time per unit or lens set)*

Run stereo calibration using a 9 × 6 checkerboard (25 mm square size):

```
python3 Stereo_V4.py --rows 6 --cols 9 --square 25
```

> This generates stereo rectification maps saved under `maps/`.

---

## Step 7 – Post-Processing and Index Generation

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

## Step 8 – GPIO Remote Trigger *(Optional)*

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
