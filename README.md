# God's Eye - Advanced Remote Monitoring System

> **STATUS**: CLASSIFIED // TOP SECRET
> **CODENAME**: PROJECT GODS EYE

God's Eye is a powerful, sci-fi themed remote monitoring and surveillance system designed for authorized administrators to track, monitor, and control devices in real-time. It features a centralized dashboard, a Telegram command interface, and a stealthy client agent.

---

## 🚀 Key Features

*   **Real-Time Monitoring**: Track CPU, RAM, Disk usage, and Online status of all devices.
*   **Live Surveillance**:
    *   **Screen Stream**: View the target's screen in real-time (MJPEG streaming).
    *   **Camera Stream**: Access the target's webcam feed remotely.
*   **Location Tracking**: IP-based geolocation visualized on an interactive map.
*   **Remote Command Execution**: Execute shell commands on target devices directly from the dashboard or Telegram.
*   **Telegram Integration**:
    *   Full control via Telegram Bot (@BotFather).
    *   Sci-Fi themed interface ("Commander Xcyberex").
    *   Interactive buttons for quick actions.
*   **Stealth Client**:
    *   Runs in the background.
    *   **Persistence**: Automatically adds itself to Windows Startup.
    *   **Zero-Config Installer**: Single `.exe` file; prompts for Server URL on first run.

---

## 🛠️ Installation & Setup

### Prerequisites
*   Python 3.9+ (for Server)
*   Windows (for Client)

### 1. Server Setup (The command center)
1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/Project_Gods_Eye.git
    cd Project_Gods_Eye
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configure Telegram Bot:
    *   Open `server/bot.py`.
    *   Set `BOT_TOKEN` to your bot token from Telegram's BotFather.
    *   (Optional) Update `app.py` secret keys if deploying publicly.

4.  Run the Server and Bot:
    *   Run `run_server.bat` (Starts Dashboard on http://localhost:5000)
    *   Run `run_bot.bat` (Starts Telegram Bot Listener)

### 2. Client Setup (The target)
**Option A: Developer Mode (Python)**
1.  Navigate to `client/`.
2.  Run `run_client.bat`.

**Option B: Standalone Executable (Recommended)**
1.  Run `build_client.bat` on your dev machine to generate the `.exe`.
2.  Copy `dist/GodsEyeAgent.exe` to the target machine.
3.  **Run `GodsEyeAgent.exe`**.
    *   **First Run**: A popup will ask for the **Server URL** (e.g., `http://YOUR_SERVER_IP:5000`).
    *   **Done**: The agent saves the config and installs itself to startup.

---

## 🖥️ Usage

### Dashboard
Access `http://localhost:5000` (or your deployed URL).
*   **Home**: List of all active/inactive devices.
*   **Device Details**: Click a device to see:
    *   System Stats (CPU/RAM).
    *   Location Map.
    *   **Live Stream Box**: Watch screen or camera feed.
    *   **Command Terminal**: Send shell commands.

### Telegram Bot
Start a chat with your bot.
*   `/start`: Initialize connection.
*   **Buttons**:
    *   `List Devices`: See active targets.
    *   `Info`: Get system stats.
    *   `Stream`: Get link to live feed.
    *   `Photo`: Snap a camera picture.
    *   `Exec`: Execute remote commands.

---

## ⚠️ Disclaimer
**This software is for EDUCATIONAL PURPOSES and AUTHORIZED MONITORING ONLY.**
Do not use this software on devices you do not own or have explicit permission to monitor. The developers assume no liability for misuse.

---

**"WE SEE EVERYTHING."**
