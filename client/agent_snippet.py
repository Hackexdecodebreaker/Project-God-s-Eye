
def control_loop():
    # Only active if enabled, checks for input events
    # This should be a separate thread that runs frequently
    while True:
        try:
            # Poll for input events
            config = load_config() # Reload config if needed or pass server_url
            server_url_local = config.get('server_url', SERVER_URL)
            
            # We need the numeric ID from the checkin response, but agent uses hardware_id.
            # We'll assume the server can map hardware_id to ID, OR we change the API to accept hardware_id.
            # Let's change server to accept hardware_id for easier agent logic.
            # Change route: /api/control/pending/<hardware_id>
            
            resp = requests.get(f"{server_url_local}/api/control/pending/{HARDWARE_ID}", timeout=1)
            if resp.status_code == 200:
                data = resp.json()
                events = data.get('events', [])
                for event in events:
                    etype = event.get('type')
                    if etype == 'mousemove':
                        # Scale coordinates?
                        # For now assume server sends absolute or relative. 
                        # Best is relative 0-1, agent scales to local res.
                        # client needs screen size.
                        w, h = pyautogui.size()
                        x = int(event['x'] * w)
                        y = int(event['y'] * h)
                        pyautogui.moveTo(x, y)
                    elif etype == 'click':
                        pyautogui.click()
                    elif etype == 'keydown':
                        key = event.get('key')
                        # Map JS keys to PyAutoGUI keys if needed
                        pyautogui.press(key)
                        
        except Exception:
            pass
        time.sleep(0.1) # 10 polls per second
