import time
import requests
import json
import os

DEVICE_IP = "10.0.4.20"
APP_ID = "weather_app"
ICON_FOLDER = "icons"  # local folder containing your icons
TEXT_COLOR = "#FFFF00FF"

cities = [
    ("Dubai", 25.2048, 55.2708),
    ("London", 51.5074, -0.1278),
    ("New York", 40.7128, -74.0060),
]

# Map Open-Meteo weather codes to icon filenames
weather_icon_map = {
    0: "sun.png",           # Clear sky
    1: "partly.png",        # Mainly clear
    2: "partly.png",        # Partly cloudy
    3: "cloud.png",         # Overcast
    45: "fog.png",          # Fog
    48: "fog.png",          # Depositing rime fog
    51: "rain.png",         # Drizzle
    53: "rain.png",
    55: "rain.png",
    61: "rain.png",         # Rain
    63: "rain.png",
    65: "rain.png",
    71: "snow.png",         # Snow
    73: "snow.png",
    75: "snow.png",
    80: "rain.png",         # Rain showers
    81: "rain.png",
    82: "rain.png",
    95: "rain.png",         # Thunderstorm
    96: "rain.png",
    99: "rain.png",
}

def get_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    cw = data.get("current_weather", {})
    temp = cw.get("temperature")
    code = cw.get("weathercode", 0)
    return temp, code

def upload_icon(local_path, filename="icon.png"):
    with open(local_path, "rb") as f:
        data = f.read()
    url = f"http://{DEVICE_IP}/api/assets/upload?app_id={APP_ID}&file={filename}"
    resp = requests.post(url, data=data, headers={"Content-Type": "application/octet-stream"})
    resp.raise_for_status()
    return filename

def display_weather(city, temp, icon_path):
    payload = {
        "app_id": APP_ID,
        "elements": [
            {
                "id": "icon",
                "timeout": 5,
                "type": "image",
                "path": icon_path,
                "x": 0,
                "y": 0
            },
            {
                "id": "city",
                "timeout": 5,
                "type": "text",
                "text": city,
                "x": 18,
                "y": 0,
                "font": "small",
                "color": "#FFFFFFFF",
                "width": 54
            },
            {
                "id": "temp",
                "timeout": 5,
                "type": "text",
                "text": f"{temp}°C",
                "x": 18,
                "y": 6,
                "font": "big",
                "color": TEXT_COLOR,
                "width": 54,
                "scroll_rate": 60
            }
        ]
    }
    url = f"http://{DEVICE_IP}/api/display/draw"
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, data=json.dumps(payload, ensure_ascii=False))
    resp.raise_for_status()

def main():
    while True:
        for city, lat, lon in cities:
            try:
                temp, code = get_weather(lat, lon)
                icon_filename = weather_icon_map.get(code, "sun.png")  # fallback to sun.png
                local_icon_path = os.path.join(ICON_FOLDER, icon_filename)
                device_icon_path = upload_icon(local_icon_path)
                display_weather(city, temp, device_icon_path)
            except Exception as e:
                print(f"Error displaying {city}: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
