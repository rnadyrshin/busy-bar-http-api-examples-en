#!/usr/bin/env python3
"""
Ping chart display for 72x16 LED device.

Features:
- Pings a target IP once per second
- Draws a simple scrolling line chart (72 px wide) in a 72x16 image
- Reserves the top 5 pixels for the current ping value shown as a small-font text element
- Uploads the image to the device and issues a draw command that overlays the small-font ping

Usage:
    python ping_chart_display.py --server 10.0.4.20 --target 1.2.3.4 --app_id my_app

Dependencies:
    pip install pillow requests

Notes:
- This script shells out to the system "ping" command; behaviour/options differ slightly between OSes.
- The script updates the device every second. Stop with Ctrl-C.
"""

import argparse
import collections
import io
import json
import os
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

STOP = False


def signal_handler(sig, frame):
    global STOP
    STOP = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def ping_once(host: str, timeout_s: float = 1.0) -> Optional[float]:
    """Ping host once and return round-trip time in ms, or None on failure."""
    system = platform.system()
    if system == "Windows":
        # Windows: use -n 1 and -w timeout_in_ms
        cmd = ["ping", "-n", "1", "-w", str(int(timeout_s * 1000)), host]
    elif system == "Darwin":
        # macOS: ping -c 1 -W is different (in ms) — use -c 1 and rely on default timeout
        cmd = ["ping", "-c", "1", host]
    else:
        # Linux: ping -c 1 -W timeout_in_seconds (integer)
        # Use -w fallback if available
        cmd = ["ping", "-c", "1", "-W", str(int(timeout_s)), host]

    try:
        completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_s + 1)
        out = completed.stdout + completed.stderr
    except Exception:
        return None

    # Parse for time=XX ms
    m = re.search(r"time[=<]([0-9]+\.?[0-9]*)\s*ms", out)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return None

    # Windows localized output might include "Average = Xms" or different formatting; try another regex
    m2 = re.search(r"Average =\s*([0-9]+)ms", out)
    if m2:
        try:
            return float(m2.group(1))
        except Exception:
            return None

    # No parse
    return None


def draw_chart_image(history, width=WIDTH, height=HEIGHT):
    """Return a bytes object containing PNG image (72x16) of the chart with black background."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # Draw grid baseline (optional): horizontal line at bottom
    # draw.line([(0, height - 1), (width - 1, height - 1)], fill=(40, 40, 40, 255))

    # Determine scale: use max of recent history (ignore None). Minimum scale at 50ms to make small pings visible
    valid_vals = [v for v in history if v is not None]
    if valid_vals:
        max_ping = max(max(valid_vals), 50.0)
    else:
        max_ping = 100.0

    # Cap to sane maximum to keep chart readable
    max_ping = min(max_ping, 2000.0)

    # map values to y coordinates in chart area (0..CHART_HEIGHT-1) where 0 is top of chart area
    points = []
    for i, v in enumerate(history):
        x = i
        if v is None:
            # put missing as bottom (i.e., high latency)
            y = CHART_HEIGHT - 1
        else:
            ratio = min(v / max_ping, 1.0)
            y = int((1.0 - ratio) * (CHART_HEIGHT - 1))
        points.append((x, CHART_Y + y))

    # Draw polyline connecting consecutive valid points
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        draw.line([(x1, y1), (x2, y2)], fill=(0, 255, 0, 255))

    # Optionally draw dots
    for x, y in points:
        draw.point((x, y), fill=(0, 200, 0, 255))

    # Return PNG bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def upload_image(server: str, app_id: str, filename: str, image_bytes: bytes):
    url = f"http://{server}/api/assets/upload?application_name={app_id}&file={filename}"
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
        "application_name": app_id,
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

        # Sleep the remainder of the interval
        elapsed = time.time() - start
        to_sleep = args.interval - elapsed
        if to_sleep > 0:
            time.sleep(to_sleep)

    print("Exiting")


if __name__ == "__main__":
    main()
