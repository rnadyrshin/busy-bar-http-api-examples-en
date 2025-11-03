import time
import requests

# Device info
DEVICE_IP = "10.0.4.20"
APP_ID = "weather_app"

# City list with coordinates
cities = [
    ("Dubai", 25.2048, 55.2708),
    ("London", 51.5074, -0.1278),
    ("New York", 40.7128, -74.0060),
]

def get_weather(lat, lon):
    # Using Open‑Meteo API to get current weather
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current_weather=true"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    j = resp.json()
    cw = j.get("current_weather", {})
    temp = cw.get("temperature")
    wind = cw.get("windspeed")
    # weathercode is numeric; you might map it to text, but for simplicity:
    code = cw.get("weathercode")
    return temp, wind, code

def display_text(text, timeout=6, font="medium", width=72, scroll_rate=60, color="#FFFFFFFF"):
    payload = {
        "app_id": APP_ID,
        "elements": [
            {
                "id": "text0",
                "timeout": timeout,
                "type": "text",
                "text": text,
                "x": 0,
                "y": 3,
                "font": font,
                "color": color,
                "width": width,
                "scroll_rate": scroll_rate,
            }
        ]
    }
    url = f"http://{DEVICE_IP}/api/display/draw"
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp

def main_loop():
    while True:
        for city, lat, lon in cities:
            try:
                temp, wind, code = get_weather(lat, lon)
                # Create a display string
                text = f"{city}: {temp:.1f}°C, wind {wind:.1f} km/h"
            except Exception as e:
                text = f"{city}: weather error"
                print("Error fetching weather for", city, ":", e)
            print("Displaying:", text)
            display_text(text)
            time.sleep(3)  # 3‑second pause before next city

if __name__ == "__main__":
    main_loop()
