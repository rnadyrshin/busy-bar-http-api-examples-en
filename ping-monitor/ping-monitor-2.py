#!/usr/bin/env python3
"""
Ping chart display for 72x16 LED device with colored bars.

Features:
- Pings a target IP once per second
- Draws a colored line chart (72 px wide) in a 72x16 image
- Bars colored based on ping: 0–20ms green, 21–50ms yellow, >50ms red
- Scale height fixed at 100ms
- Reserves the top 5 pixels for the current ping value shown as a small-font text element
- Uploads the image to the device and issues a draw command that overlays the small-font ping

Usage:
    python ping_chart_display.py --server 10.0.4.20 --target 1.2.3.4 --app_id my_app

Dependencies:
    pip install pillow requests
"""

import argparse
import collections
import io
import json
import platform
import re
import signal
import subprocess
import sys
import time
from typing import Optional

import requests
from PIL import Image, ImageDraw

WIDTH = 72
HEIGHT = 16
TOP_TEXT_HEIGHT = 5  # small font height on device
CHART_Y = TOP_TEXT_HEIGHT
CHART_HEIGHT = HEIGHT - TOP_TEXT_HEIGHT  # 11
HISTORY_LENGTH = WIDTH
MAX_PING = 100.0  # Scale height fixed at 100ms

STOP = False


def signal_handler(sig, frame):
    global STOP
    STOP = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def ping_once(host: str, timeout_s: float = 1.0) -> Optional[float]:
    system = platform.system()
    if system == "Windows":
        cmd = ["ping", "-n", "1", "-w", str(int(timeout_s * 1000)), host]
    elif system == "Darwin":
        cmd = ["ping", "-c", "1", host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(int(timeout_s)), host]

    try:
        completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_s + 1)
        out = completed.stdout + completed.stderr
    except Exception:
        return None

    m = re.search(r"time[=<]([0-9]+\.?[0-9]*)\s*ms", out)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return None

    m2 = re.search(r"Average =\s*([0-9]+)ms", out)
    if m2:
        try:
            return float(m2.group(1))
        except Exception:
            return None

    return None


def get_color_for_ping(ping: Optional[float]) -> tuple[int,int,int,int]:
    if ping is None:
        return (128, 128, 128, 255)  # gray for missing
    if ping <= 20:
        return (0, 255, 0, 255)  # green
    elif ping <= 50:
        return (255, 255, 0, 255)  # yellow
    else:
        return (255, 0, 0, 255)  # red


def draw_chart_image(history, width=WIDTH, height=HEIGHT):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    for i, ping in enumerate(history):
        if ping is None:
            ping_val = MAX_PING
        else:
            ping_val = min(ping, MAX_PING)
        ratio = ping_val / MAX_PING
        y = int((1.0 - ratio) * (CHART_HEIGHT - 1))
        color = get_color_for_ping(ping)
        # Draw vertical line (1px wide) for the ping value
        draw.line([(i, CHART_Y + CHART_HEIGHT - 1), (i, CHART_Y + y)], fill=color)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def upload_image(server: str, app_id: str, filename: str, image_bytes: bytes):
    url = f"http://{server}/api/assets/upload?app_id={app_id}&file={filename}"
    headers = {"Content-Type": "application/octet-stream"}
    try:
        resp = requests.post(url, headers=headers, data=image_bytes, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"Upload failed: {e}")
        return False
    return True


def send_draw_command(server: str, app_id: str, image_path: str, ping_text: str, timeout=2):
    url = f"http://{server}/api/display/draw"
    payload = {
        "app_id": app_id,
        "elements": [
            {
                "id": "img",
                "timeout": timeout,
                "type": "image",
                "path": image_path,
                "x": 0,
                "y": 0,
            },
            {
                "id": "txt",
                "timeout": timeout,
                "type": "text",
                "text": ping_text,
                "x": 0,
                "y": 0,
                "font": "small",
                "color": "#FFFFFFFF",
                "width": 20,
                "scroll_rate": 0,
            },
        ],
    }
    try:
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print(f"Draw command failed: {e}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True, help="Device IP or host (e.g. 10.0.4.20)")
    parser.add_argument("--target", required=True, help="Target game server IP or hostname to ping")
    parser.add_argument("--app_id", default="my_app", help="app_id to use when uploading/displaying")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between updates (default 1.0)")
    parser.add_argument("--fname", default="ping_chart.png", help="Filename to upload to device")
    args = parser.parse_args()

    history = collections.deque([None] * HISTORY_LENGTH, maxlen=HISTORY_LENGTH)

    print(f"Starting ping chart: target={args.target} -> device={args.server} (app_id={args.app_id})")
    while not STOP:
        start = time.time()
        ping_ms = ping_once(args.target, timeout_s=0.9)
        if ping_ms is None:
            ping_text = "-- ms"
        else:
            ping_text = f"{int(round(ping_ms))}ms"

        history.append(ping_ms)

        png_bytes = draw_chart_image(list(history))

        ok = upload_image(args.server, args.app_id, args.fname, png_bytes)
        if not ok:
            print("Upload failed; retrying on next loop")
        else:
            ok2 = send_draw_command(args.server, args.app_id, args.fname, ping_text, timeout=int(max(args.interval * 1.5, 2)))
            if not ok2:
                print("Draw command failed")

        elapsed = time.time() - start
        to_sleep = args.interval - elapsed
        if to_sleep > 0:
            time.sleep(to_sleep)

    print("Exiting")


if __name__ == "__main__":
    main()
