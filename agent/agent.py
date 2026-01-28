import psutil
import socket
import requests
import time
import subprocess

API_KEY = "enter your api key"
SERVER_URL = "http://129.151.45.70:5000/api/update"

def get_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "unknown"

def get_brand():
    try:
        result = subprocess.check_output(
            "wmic computersystem get manufacturer,model",
            shell=True
        ).decode(errors="ignore")
        return result.replace("\n", " ").strip()
    except:
        return "Unknown"

def send_data():
    data = {
        "api_key": API_KEY,
        "cpu": psutil.cpu_percent(interval=1),
        "ram": psutil.virtual_memory().percent,
        "battery": psutil.sensors_battery().percent if psutil.sensors_battery() else -1,
        "ip": get_ip(),
        "brand": get_brand()
    }

    try:
        r = requests.post(SERVER_URL, json=data, timeout=5)
        print("Sent:", r.status_code)
    except Exception as e:
        print("Error:", e)

print("PC Monitoring Agent Started...")
while True:
    send_data()
    time.sleep(10)
