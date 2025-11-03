import time
import requests
from PIL import Image, ImageDraw

DEVICE_IP = "10.0.4.20"
APP_ID = "weather_app"

# Cities and their coordinates
cities = [
    ("Dubai", 25.2048, 55.2708),
    ("London", 51.5074, -0.1278),
    ("New York", 40.7128, -74.0060),
]

# Light yellow color
TEXT_COLOR = "#FFFF00FF"

# Map basic weather codes to icons
def generate_icon(weather_code):
    # Create a 16x16 RGBA image
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if weather_code in ["clear", "sunny"]:
        # Draw sun
        draw.ellipse((2, 2, 13, 13), fill=(255, 255, 0, 255))
    elif weather_code in ["cloudy", "partly cloudy"]:
        draw.ellipse((1, 6, 15, 13), fill=(200, 200, 200, 255))
        draw.ellipse((4, 2, 12, 10), fill=(180, 180, 180, 255))
    elif weather_code in ["rain"]:
        draw.rectangle((3, 5, 12, 12), fill=(100, 100, 255, 255))
    else:
        draw.rectangle((0, 0, 15, 15), fill=(150, 150, 150, 255))  # unknown
    return img

# Convert PIL image to raw bytes
def pil_to_bytes(img):
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# Get current weather from Open-Meteo
def get_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    cw = data.get("current_weather", {})
    temp = cw.get("temperature")
    code = cw.get("weathercode", 0)
    # Map code to string
    if code == 0:
        code_str = "clear"
    elif code in [1, 2, 3]:
        code_str = "cloudy"
    elif code in [61, 63, 65]:
        code_str = "rain"
    else:
        code_str = "unknown"
    return temp, code_str

# Upload the icon to the device
def upload_icon(img_bytes, filename="icon.png"):
    url = f"http://{DEVICE_IP}/api/assets/upload?app_id={APP_ID}&file={filename}"
    resp = requests.post(url, data=img_bytes, headers={"Content-Type": "application/octet-stream"})
    resp.raise_for_status()
    return filename

# Display the weather on the screen
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
    resp = requests.post(url, json=payload)
    resp.raise_for_status()

def main():
    while True:
        for city, lat, lon in cities:
            try:
                temp, weather_code = get_weather(lat, lon)
                icon_img = generate_icon(weather_code)
                icon_bytes = pil_to_bytes(icon_img)
                icon_path = upload_icon(icon_bytes)
                display_weather(city, temp, icon_path)
            except Exception as e:
                print(f"Error displaying {city}: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
