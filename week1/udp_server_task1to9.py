"""
UDP Bidirectional Server (Reply-on-receive)

UDP is connectionless:
- Server binds and waits for datagrams.
- For every message received:
    * prints it
    * asks the server user to type a reply
    * replies using sendto() to the sender's address

Safe termination (initiated from client side):
- "stop server" : server exits
- "stop client" : server replies but continues running
"""

import socket

HOST = "127.0.0.1"
PORT = 5001
RECV_BUFFER = 1024  # bytes

def run_server() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_sock:
        server_sock.bind((HOST, PORT))
        print(f"[UDP SERVER] Listening on {HOST}:{PORT}")

        while True:
            data, client_addr = server_sock.recvfrom(RECV_BUFFER)
            msg = data.decode("utf-8", errors="replace").strip()
            print(f"[UDP SERVER] From {client_addr} -> {msg}")

            if msg.lower() == "stop server":
                server_sock.sendto(b"Server shutting down. Bye!\n", client_addr)
                break

            if msg.lower() == "stop client":
                server_sock.sendto(b"Client may stop safely. Bye!\n", client_addr)
                continue
            '''
            # Task 5-9: Bidirectional part: type a reply and send it back
            #reply_text = input("Server reply> ").strip() #uncomment for input option for server as well
            reply_text ="msg received at server"
            if not reply_text:
                reply_text = "(empty reply)"

            server_sock.sendto((reply_text + "\n").encode("utf-8"), client_addr)
            '''
        print("[UDP SERVER] Server terminated.")

if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n[UDP SERVER] KeyboardInterrupt -> Server terminated.")
