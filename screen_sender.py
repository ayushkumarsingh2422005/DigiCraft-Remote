import argparse
import json
import socket
import struct
import threading
import time

import cv2
import mss
import numpy as np
import pyautogui


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture and stream screen frames to a receiver."
    )
    parser.add_argument(
        "--host",
        required=True,
        help="Receiver IP address (for example: 192.168.1.10)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9999,
        help="Receiver port (default: 9999)",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=12.0,
        help="Target frame rate (default: 12)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=65,
        help="JPEG quality 1-100 (default: 65)",
    )
    parser.add_argument(
        "--monitor",
        type=int,
        default=1,
        help="Monitor number from mss.monitors (default: 1)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Resize factor before sending, e.g. 0.75 (default: 1.0)",
    )
    parser.add_argument(
        "--allow-control",
        action="store_true",
        help="Allow receiver to control mouse/keyboard on this PC",
    )
    parser.add_argument(
        "--token",
        default="",
        help="Optional shared token for basic access control",
    )
    return parser.parse_args()


def send_packet(sock: socket.socket, packet_type: bytes, payload: bytes) -> None:
    sock.sendall(packet_type + struct.pack("!I", len(payload)))
    sock.sendall(payload)


def recv_exact(sock: socket.socket, size: int) -> bytes:
    buf = bytearray()
    while len(buf) < size:
        chunk = sock.recv(size - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed while receiving data.")
        buf.extend(chunk)
    return bytes(buf)


def recv_packet(sock: socket.socket) -> tuple[bytes, bytes]:
    header = recv_exact(sock, 5)
    packet_type = header[:1]
    (size,) = struct.unpack("!I", header[1:])
    payload = recv_exact(sock, size)
    return packet_type, payload


def apply_control_event(event: dict, monitor: dict) -> None:
    etype = event.get("type")
    if etype == "mouse_move":
        x = int(event.get("x", 0))
        y = int(event.get("y", 0))
        pyautogui.moveTo(monitor["left"] + x, monitor["top"] + y)
    elif etype == "mouse_click":
        x = int(event.get("x", 0))
        y = int(event.get("y", 0))
        button = event.get("button", "left")
        action = event.get("action", "down")
        pyautogui.moveTo(monitor["left"] + x, monitor["top"] + y)
        if action == "down":
            pyautogui.mouseDown(button=button)
        elif action == "up":
            pyautogui.mouseUp(button=button)
    elif etype == "mouse_scroll":
        amount = int(event.get("amount", 0))
        pyautogui.scroll(amount)
    elif etype == "key":
        key = str(event.get("key", "")).lower().strip()
        action = event.get("action", "press")
        if key:
            if action == "down":
                pyautogui.keyDown(key)
            elif action == "up":
                pyautogui.keyUp(key)
            else:
                pyautogui.press(key)
    elif etype == "type_text":
        text = str(event.get("text", ""))
        if text:
            pyautogui.write(text)


def control_listener(
    sock: socket.socket,
    monitor: dict,
    allow_control: bool,
    stop_event: threading.Event,
) -> None:
    while not stop_event.is_set():
        try:
            packet_type, payload = recv_packet(sock)
        except (ConnectionError, OSError):
            stop_event.set()
            return

        if packet_type != b"C":
            continue
        if not allow_control:
            continue

        try:
            event = json.loads(payload.decode("utf-8"))
            apply_control_event(event, monitor)
        except Exception:
            # Ignore malformed/unhandled control packets to keep streaming stable.
            continue


def main() -> None:
    args = parse_args()
    jpeg_quality = max(1, min(100, args.quality))
    frame_interval = 1.0 / max(1.0, args.fps)
    pyautogui.FAILSAFE = True

    print(f"Connecting to receiver {args.host}:{args.port} ...")
    sock = socket.create_connection((args.host, args.port), timeout=10)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    print("Connected. Streaming started. Press Ctrl+C to stop.")

    with mss.mss() as sct:
        if args.monitor < 1 or args.monitor >= len(sct.monitors):
            raise ValueError(
                f"Invalid monitor {args.monitor}. Available: 1 to {len(sct.monitors) - 1}"
            )
        monitor = sct.monitors[args.monitor]
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
        stop_event = threading.Event()

        hello = {
            "monitor_width": int(monitor["width"]),
            "monitor_height": int(monitor["height"]),
            "allow_control": bool(args.allow_control),
            "token": args.token,
        }
        send_packet(sock, b"I", json.dumps(hello).encode("utf-8"))

        listener_thread = threading.Thread(
            target=control_listener,
            args=(sock, monitor, args.allow_control, stop_event),
            daemon=True,
        )
        listener_thread.start()

        try:
            while not stop_event.is_set():
                start = time.perf_counter()

                raw = sct.grab(monitor)
                frame = np.array(raw)[:, :, :3]  # BGRA -> BGR

                if args.scale != 1.0:
                    frame = cv2.resize(
                        frame,
                        dsize=None,
                        fx=args.scale,
                        fy=args.scale,
                        interpolation=cv2.INTER_AREA,
                    )

                ok, encoded = cv2.imencode(".jpg", frame, encode_params)
                if not ok:
                    continue

                send_packet(sock, b"F", encoded.tobytes())

                elapsed = time.perf_counter() - start
                sleep_for = frame_interval - elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)
        except (KeyboardInterrupt, ConnectionError, OSError):
            print("\nStopping stream...")
        finally:
            stop_event.set()
            sock.close()
            print("Connection closed.")


if __name__ == "__main__":
    main()
