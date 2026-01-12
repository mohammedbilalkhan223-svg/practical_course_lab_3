# tcp_sender.py
import socket, struct, time

SERVER = ("127.0.0.1", 20001)
SIZES = [8, 64, 256, 1024, 4096]

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(SERVER)
print("[TCP SEND] connected")

def digits_payload(n: int) -> bytes:
    return bytes((ord('0') + (i % 10) for i in range(n)))

seq = 0
try:
    for seq in range(50):
        size = SIZES[seq % len(SIZES)]

        header = f"seq={seq} size={size} ".encode()
        body_len = max(0, size - len(header))
        payload = (header + digits_payload(body_len))[:size]

        # length prefix (4 bytes) + payload
        sock.sendall(struct.pack("!I", len(payload)) + payload)

        print(f"[TCP SEND] sent seq={seq} ({len(payload)} bytes)")
        seq += 1
        time.sleep(0.02)  # faster = easier to trigger congestion + loss
except KeyboardInterrupt:
    pass
finally:
    sock.close()
    print("[TCP SEND] closed")

