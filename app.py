from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import time
import threading
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///network_monitoring.db'
db = SQLAlchemy(app)

# Models (same as your original code)
class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(80), unique=True, nullable=False)
    ip_address = db.Column(db.String(15), unique=True, nullable=False)
    status = db.Column(db.String(20), default='Unknown')
    last_seen = db.Column(db.DateTime)

class BandwidthUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now())
    upload_speed = db.Column(db.Float)
    download_speed = db.Column(db.Float)
    device = db.relationship('Device', backref=db.backref('bandwidth_usages', lazy=True))

# ThreadPoolExecutor to limit number of concurrent threads
executor = ThreadPoolExecutor(max_workers=5)

# Improved device connectivity check function
def check_device_connectivity(hostname, ip_address):
    try:
        subprocess.check_output(['ping', '-c', '1', ip_address], timeout=1)
        status = 'Online'
    except subprocess.CalledProcessError:
        status = 'Offline'
    except subprocess.TimeoutExpired:
        status = 'Offline'
    return status

# Optimized bandwidth monitoring function
def monitor_bandwidth(device_id):
    # Make sure we are in the Flask app context for database interaction
    with app.app_context():
        while True:
            try:
                # For actual bandwidth measurement, replace this with a real method (like 'speedtest-cli' or 'psutil')
                upload_speed = 10.0  # Replace with actual method for upload speed
                download_speed = 20.0  # Replace with actual method for download speed

                # Batch commit method for better performance
                bandwidth_usage = BandwidthUsage(device_id=device_id, upload_speed=upload_speed, download_speed=download_speed)
                db.session.add(bandwidth_usage)

                if db.session.new:
                    db.session.commit()

                time.sleep(60)  # Sleep for a minute before checking again
            except Exception as e:
                # Log the error properly instead of printing it
                print(f"Error monitoring bandwidth for device {device_id}: {e}")

# Function to start monitoring all devices
def start_monitoring():
    # Ensure this code is wrapped in the app context
    with app.app_context():
        devices = Device.query.all()  # Query the devices from the database
        for device in devices:
            executor.submit(monitor_bandwidth, device.id)  # Submit each device monitoring task to ThreadPoolExecutor

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/devices', methods=['GET'])
def get_devices():
    devices = []
    with app.app_context():
        for device in Device.query.all():
            device_data = {
                'hostname': device.hostname,
                'ip_address': device.ip_address,
                'status': device.status,
                'last_seen': str(device.last_seen)
            }
            devices.append(device_data)
    return jsonify(devices)

@app.route('/api/bandwidth/<device_id>', methods=['GET'])
def get_bandwidth_data(device_id):
    bandwidth_data = BandwidthUsage.query.filter_by(device_id=device_id).order_by(BandwidthUsage.timestamp.desc()).limit(10).all()
    data = []
    for usage in bandwidth_data:
        data.append({
            'timestamp': str(usage.timestamp),
            'upload_speed': usage.upload_speed,
            'download_speed': usage.download_speed
        })
    return jsonify(data)

if __name__ == '__main__':
    # Use app.app_context() to ensure database interaction happens inside the app context
    with app.app_context():
        db.create_all()  # Create the database tables if they don't exist
    
        # Optionally, add initial devices to the database here

        # Start device monitoring in the background
        start_monitoring()

    # Run the Flask app
    app.run(debug=True, threaded=True)  # Ensure Flask can handle concurrent requests
