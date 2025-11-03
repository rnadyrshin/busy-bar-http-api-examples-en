import requests
from datetime import datetime
import time

DEVICE_IP = "10.0.4.20"
APP_ID = "my_app"

# Screen width in pixels
SCREEN_WIDTH = 72

# Font widths in pixels per character
FONT_WIDTHS = {
    "small": 4,
    "medium": 5,
    "big": 7
}

def center_x(text, font, shift=0):
    text_width = len(text) * FONT_WIDTHS[font]
    x = max((SCREEN_WIDTH - text_width) // 2 + shift, 0)
    return x

while True:
    now = datetime.now()
    date_str = now.strftime("%d.%m.%Y")
    time_str = now.strftime("%H:%M:%S")
    
    payload = {
        "app_id": APP_ID,
        "elements": [
            {
                "id": "date",
                "type": "text",
                "text": date_str,
                "x": center_x(date_str, "small", shift=3),
                "y": 0,
                "font": "small",
                "color": "#FFFFFFFF",  # white
                "width": SCREEN_WIDTH,
                "scroll_rate": 60,
                "timeout": 0  # 0 = continuous display
            },
            {
                "id": "time",
                "type": "text",
                "text": time_str,
                "x": center_x(time_str, "big", shift=3),
                "y": 6,
                "font": "big",
                "color": "#AAFF00FF",  # light green
                "width": SCREEN_WIDTH,
                "scroll_rate": 60,
                "timeout": 0
            }
        ]
    }

    try:
        response = requests.post(f"http://{DEVICE_IP}/api/display/draw", json=payload)
        if not response.ok:
            print("Failed to update display:", response.text)
    except Exception as e:
        print("Error:", e)
    
    time.sleep(1)
