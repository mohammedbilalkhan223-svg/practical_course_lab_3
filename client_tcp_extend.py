import socket

HOST = "127.0.0.1"
PORT = 65438

def start_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    print("TCP Client started and connected to server.")

    try:
        while True:
            message = input("Enter message: ")
            client_socket.sendall(message.encode())

            if message.lower() == "stop client":
                print("Stopping client...")
                break

            if message.lower() == "stop server":
                print("Server requested shutdown. Closing client.")
                break

            # Receive reply from server
            response = client_socket.recv(1024).decode()
            print(f"Server: {response}")



    finally:
        client_socket.close()
        print("Client terminated.")

if __name__ == "__main__":
    start_client()
