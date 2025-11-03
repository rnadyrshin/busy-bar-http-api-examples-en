import requests
from datetime import datetime

DEVICE_IP = "10.0.4.20"
APP_ID = "my_app"

# Get current date and time
now = datetime.now()
date_str = now.strftime("%d.%m.%Y")
time_str = now.strftime("%H:%M:%S")

# Screen width in pixels
SCREEN_WIDTH = 72

# Font widths in pixels per character
FONT_WIDTHS = {
    "small": 4,
    "medium": 5,
    "big": 7
}

def center_x(text, font):
    text_width = len(text) * FONT_WIDTHS[font]
    x = max((SCREEN_WIDTH - text_width) // 2, 0)
    return x

# Prepare JSON payload
payload = {
    "app_id": APP_ID,
    "elements": [
        {
            "id": "date",
            "type": "text",
            "text": date_str,
            "x": center_x(date_str, "small"),
            "y": 0,  # top row
            "font": "small",
            "color": "#FFFFFFFF",  # white
            "width": SCREEN_WIDTH,
            "scroll_rate": 60,
            "timeout": 6
        },
        {
            "id": "time",
            "type": "text",
            "text": time_str,
            "x": center_x(time_str, "big"),
            "y": 6,  # leaving 1px margin from date
            "font": "big",
            "color": "#FFFFFFFF",  # white
            "width": SCREEN_WIDTH,
            "scroll_rate": 60,
            "timeout": 6
        }
    ]
}

# Send the request
response = requests.post(f"http://{DEVICE_IP}/api/display/draw", json=payload)

if response.ok:
    print("Date and time displayed successfully!")
else:
    print("Failed to display:", response.text)
