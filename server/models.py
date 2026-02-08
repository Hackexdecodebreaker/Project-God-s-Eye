from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hardware_id = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100))
    ip_address = db.Column(db.String(50))
    os_info = db.Column(db.String(200))
    last_seen = db.Column(db.DateTime, default=datetime.now)
    cpu_usage = db.Column(db.Float)
    ram_usage = db.Column(db.Float)
    total_ram = db.Column(db.Float)
    location_lat = db.Column(db.Float)
    location_lon = db.Column(db.Float)
    is_online = db.Column(db.Boolean, default=False)

    commands = db.relationship('Command', backref='device', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'hardware_id': self.hardware_id,
            'name': self.name,
            'ip_address': self.ip_address,
            'os_info': self.os_info,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'cpu_usage': self.cpu_usage,
            'ram_usage': self.ram_usage,
            'total_ram': self.total_ram,
            'location_lat': self.location_lat,
            'location_lon': self.location_lon,
            'is_online': self.is_online
        }

class Command(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    command_text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending') # pending, executed, failed
    output = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    executed_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'device_id': self.device_id,
            'command_text': self.command_text,
            'status': self.status,
            'output': self.output,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None
        }
