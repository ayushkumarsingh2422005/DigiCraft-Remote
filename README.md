# Python Screen Share (Sender + Receiver)

This project has 2 scripts:

- `screen_sender.py` -> captures your screen and sends video frames
- `screen_receiver.py` -> receives frames and shows live screen

Works on Windows.  
Can run on same Wi-Fi/LAN or over global internet.

---

## 1) Requirements

- Windows PC on both sides
- Python 3.9+ installed
- Internet connection

Install packages on both PCs:

```bash
pip install -r requirements.txt
```

---

## 2) Files

- `screen_sender.py` - run on the PC that shares screen
- `screen_receiver.py` - run on the PC that watches screen
- `requirements.txt` - dependencies (`opencv-python`, `mss`, `numpy`)

---

## 3) Quick Test on Same Network (LAN)

### On receiver PC

```bash
python screen_receiver.py --host 0.0.0.0 --port 9999
```

### On sender PC

Use receiver local IP (example `192.168.1.50`):

```bash
python screen_sender.py --host 192.168.1.50 --port 9999
```

---

## 4) Run Over Global Internet (Different Routers)

If both PCs are on different networks, direct local IP will NOT work.

Use one of these methods:

1. Tailscale (recommended, easiest)
2. Port forwarding + public IP

### Method A: Tailscale (Recommended)

No code change needed.

1. Install Tailscale on both PCs.
2. Login with the same Tailscale account.
3. Get receiver Tailscale IP (looks like `100.x.x.x`).
4. Start receiver:

```bash
python screen_receiver.py --host 0.0.0.0 --port 9999
```

5. Start sender using receiver Tailscale IP:

```bash
python screen_sender.py --host 100.x.x.x --port 9999
```

### Method B: Port Forwarding

1. On receiver router, forward TCP port `9999` to receiver PC local IP.
2. Find receiver public IP.
3. Start receiver:

```bash
python screen_receiver.py --host 0.0.0.0 --port 9999
```

4. Start sender with receiver public IP:

```bash
python screen_sender.py --host <receiver_public_ip> --port 9999
```

Note: If receiver uses CGNAT/double NAT, port forwarding may fail. In that case use Tailscale.

---

## 5) Sender Options

```bash
python screen_sender.py --host <ip> --port 9999 --fps 12 --quality 65 --scale 1.0 --monitor 1
```

- `--host` (required): receiver IP
- `--port`: receiver port (default `9999`)
- `--fps`: target frame rate (default `12`)
- `--quality`: JPEG quality 1-100 (default `65`)
- `--scale`: frame resize factor (default `1.0`)
- `--monitor`: monitor index (default `1`)

### Example (better for slow internet)

```bash
python screen_sender.py --host 100.64.20.5 --port 9999 --fps 10 --quality 55 --scale 0.7
```

---

## 6) Stop Streaming

- Receiver: focus video window and press `q`
- Sender: press `Ctrl + C`

---

## 7) Troubleshooting

### Connection refused / timeout

- Check receiver script is running first
- Check IP and port are correct
- Allow Python in Windows Defender Firewall
- Try changing port to `10000` on both sides

### Black screen / no window update

- Keep sender screen unlocked and active
- Lower fps and quality:

```bash
python screen_sender.py --host <ip> --fps 8 --quality 45 --scale 0.6
```

### Over internet not connecting

- Prefer Tailscale
- If using port forwarding, verify router rule and public IP
- ISP CGNAT can block inbound connection

---

## 8) Security Note

Current version is basic TCP stream with no authentication/encryption.
Use only with trusted users/networks. For stronger security, add auth token + TLS.
