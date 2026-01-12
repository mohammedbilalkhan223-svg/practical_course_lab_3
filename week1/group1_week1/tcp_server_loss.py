# tcp_receiver.py
import socket, struct, time

LISTEN = ("127.0.0.1", 20001)
CHUNK = 256
PROCESSING_DELAY = 0.05  # increase to make receiver “slow” and build pressure

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(LISTEN)
srv.listen(1)
print("[TCP RECV] listening", LISTEN)

conn, addr = srv.accept()
print("[TCP RECV] connected", addr)

def recvn(n: int) -> bytes:
    data = b""
    while len(data) < n:
        part = conn.recv(min(CHUNK, n - len(data)))
        if not part:
            raise ConnectionError("peer closed")
        data += part
    return data

try:
    while True:
        hdr = recvn(4)
        (length,) = struct.unpack("!I", hdr)
        payload = recvn(length)

        print(f"[TCP RECV] got {length} bytes | {payload[:60]!r}")
        time.sleep(PROCESSING_DELAY)
except (KeyboardInterrupt, ConnectionError) as e:
    print("[TCP RECV] stop:", e)
finally:
    conn.close()
    srv.close()
    print("[TCP RECV] closed")

