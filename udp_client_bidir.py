"""
UDP Bidirectional Client

- Sends messages to server at HOST:PORT
- Waits for reply datagram after each send and prints it

Safe termination (initiated from client side):
- "stop client" : client exits (server continues)
- "stop server" : requests server shutdown
"""

import socket

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5001
RECV_BUFFER = 1024  # bytes

def run_client() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_sock:
        # Timeout prevents infinite blocking if server is down / packet lost
        client_sock.settimeout(10.0)

        print(f"[UDP CLIENT] Sending to {SERVER_HOST}:{SERVER_PORT}")
        print("[UDP CLIENT] Commands: 'stop client' or 'stop server'")

        while True:
            msg = input("You> ").strip()
            if not msg:
                continue

            client_sock.sendto((msg + "\n").encode("utf-8"), (SERVER_HOST, SERVER_PORT))

            try:
                data, _ = client_sock.recvfrom(RECV_BUFFER)
                print("Server>", data.decode("utf-8", errors="replace").strip())
            except socket.timeout:
                print("[UDP CLIENT] No reply (timeout).")

            if msg.lower() in ("stop client", "stop server"):
                print("[UDP CLIENT] Terminating now.")
                break

if __name__ == "__main__":
    try:
        run_client()
    except KeyboardInterrupt:
        print("\n[UDP CLIENT] KeyboardInterrupt -> Client terminated.")
