import socket, struct, time

SERVER = ("127.0.0.1", 20001)

# Different payload sizes (bytes)
SIZES = [8, 64, 256, 1024, 4096, 16384]

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(SERVER)
print("[TCP SENDER] connected")
seq = 0
try:
    for seq in range(50):
        size = SIZES[seq % len(SIZES)]

        # digit pattern like before: 0123456789 repeating
        payload = bytes((ord('0') + (i % 10)) for i in range(size))

        # length-prefix framing: 4 bytes network-order length
        sock.sendall(struct.pack("!I", len(payload)) + payload)
        print(f"[TCP SENDER] sent seq={seq}, {len(payload)} bytes")

        seq += 1
        time.sleep(0.05)  # increase rate to stress receiver
except KeyboardInterrupt:
    pass
finally:
    sock.close()
    print("[TCP SENDER] closed")

