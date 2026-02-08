import os
import sys
import winreg as reg
import psutil
import tkinter as tk
from tkinter import messagebox

def remove_from_startup():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_ALL_ACCESS)
        reg.DeleteValue(key, "GodsEyeAgent")
        reg.CloseKey(key)
        return True, "Registry key removed successfully."
    except FileNotFoundError:
        return True, "Registry key not found (already removed)."
    except Exception as e:
        return False, f"Failed to remove Registry key: {e}"

def terminate_agent():
    count = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            # Check for both the executable name and python processes running the agent script
            if proc.info['name'].lower() == "godseyeagent.exe":
                proc.terminate()
                count += 1
            elif "python" in proc.info['name'].lower():
                for cmd in proc.cmdline():
                    if "agent.py" in cmd.lower():
                        proc.terminate()
                        count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return count

def main():
    # Hide main tkinter window
    root = tk.Tk()
    root.withdraw()

    reg_success, reg_msg = remove_from_startup()
    proc_count = terminate_agent()

    final_msg = f"Cleanup complete.\n\nRegistry: {reg_msg}\nProcesses Terminated: {proc_count}"
    
    if reg_success:
        messagebox.showinfo("God's Eye - Anti-Agent", final_msg)
    else:
        messagebox.showerror("God's Eye - Anti-Agent", final_msg)

if __name__ == "__main__":
    main()
