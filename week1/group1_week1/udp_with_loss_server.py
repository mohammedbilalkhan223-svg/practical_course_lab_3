# udp_recv.py
import socket

BIND = ("127.0.0.1", 20001)
BUF = 65535   # large buffer → no truncation

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(BIND)
print("[UDP RECV] listening", BIND)

expected = 0

while True:
    data, addr = sock.recvfrom(BUF)

    # Extract seq number from header: "seq=<n> size=<m> "
    try:
        txt = data[:60].decode(errors="ignore")
        seq = int(txt.split("seq=")[1].split()[0])
    except Exception:
        seq = None

    if seq is not None:
        if seq != expected:
            print(f"[UDP RECV] GAP detected: expected {expected}, got {seq}")
            expected = seq
        expected += 1
    if data == b'quit_server':
        print("stopping now")
        break
    print(f"[UDP RECV] got {len(data)} bytes from {addr} | preview={data[:40]!r}")

sock.close()