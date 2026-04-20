import argparse
import socket
import struct
import time

import cv2
import mss
import numpy as np


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
    return parser.parse_args()


def send_exact(sock: socket.socket, payload: bytes) -> None:
    sock.sendall(struct.pack("!I", len(payload)))
    sock.sendall(payload)


def main() -> None:
    args = parse_args()
    jpeg_quality = max(1, min(100, args.quality))
    frame_interval = 1.0 / max(1.0, args.fps)

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

        try:
            while True:
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

                send_exact(sock, encoded.tobytes())

                elapsed = time.perf_counter() - start
                sleep_for = frame_interval - elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)
        except KeyboardInterrupt:
            print("\nStopping stream...")
        finally:
            sock.close()
            print("Connection closed.")


if __name__ == "__main__":
    main()
