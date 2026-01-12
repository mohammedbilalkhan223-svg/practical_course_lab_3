import socket, struct, time

LISTEN = ("127.0.0.1", 20001)

# Congestion knobs
RECV_CHUNK = 64
PROCESSING_DELAY = 0.10

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(LISTEN)
srv.listen(1)
print("[TCP RECV] listening")

conn, addr = srv.accept()
print("[TCP RECV] connected:", addr)

def recvn(n: int) -> bytes:
    """Read exactly n bytes from TCP stream."""
    data = b""
    while len(data) < n:
        chunk = conn.recv(min(RECV_CHUNK, n - len(data)))
        if not chunk:
            raise ConnectionError("peer closed")
        data += chunk
    return data

try:
    while True:
        hdr = recvn(4)
        (length,) = struct.unpack("!I", hdr)
        payload = recvn(length)

        print(f"[TCP RECV] got message {length} bytes | preview={payload[:40]!r}")
        time.sleep(PROCESSING_DELAY)
except (KeyboardInterrupt, ConnectionError) as e:
    print("[TCP RECV] stopping:", e)
finally:
    conn.close()
    srv.close()
    print("[TCP RECV] closed")

