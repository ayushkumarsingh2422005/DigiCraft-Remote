import argparse
import socket
import struct

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Receive and display a remote screen stream."
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind address (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9999,
        help="Port to listen on (default: 9999)",
    )
    return parser.parse_args()


def recv_exact(sock: socket.socket, size: int) -> bytes:
    buf = bytearray()
    while len(buf) < size:
        chunk = sock.recv(size - len(buf))
        if not chunk:
            raise ConnectionError("Connection closed while receiving data.")
        buf.extend(chunk)
    return bytes(buf)


def main() -> None:
    args = parse_args()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((args.host, args.port))
    server.listen(1)

    print(f"Waiting for sender on {args.host}:{args.port} ...")
    conn, addr = server.accept()
    print(f"Connected by {addr[0]}:{addr[1]}")
    print("Press 'q' in the video window to quit.")

    window_name = "Remote Screen"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    try:
        while True:
            header = recv_exact(conn, 4)
            (frame_size,) = struct.unpack("!I", header)
            payload = recv_exact(conn, frame_size)

            img_array = np.frombuffer(payload, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            cv2.imshow(window_name, frame)
            if (cv2.waitKey(1) & 0xFF) == ord("q"):
                break
    except (ConnectionError, OSError) as exc:
        print(f"Connection ended: {exc}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
        server.close()
        cv2.destroyAllWindows()
        print("Receiver stopped.")


if __name__ == "__main__":
    main()
