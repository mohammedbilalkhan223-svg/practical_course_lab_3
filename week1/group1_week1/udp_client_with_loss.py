# udp_send.py
import socket, time

DEST = ("127.0.0.1", 20001)
SIZES = [8, 64, 256, 1024, 4096]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def digits_payload(n: int) -> bytes:
    return bytes((ord('0') + (i % 10) for i in range(n)))

seq = 0
for expected in range(50):
    size = SIZES[seq % len(SIZES)]

    header = f"seq={seq} size={size} ".encode()
    body_len = max(0, size - len(header))
    payload = (header + digits_payload(body_len))[:size]

    sock.sendto(payload, DEST)
    print(f"[UDP SEND] sent seq={seq} ({len(payload)} bytes)")

    seq += 1
    if seq == 50:
        sock.sendto(b'quit_server', DEST)
        print("quitting server")
    time.sleep(0.05)

