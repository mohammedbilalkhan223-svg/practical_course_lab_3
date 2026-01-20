import socket

HOST = "127.0.0.1"   # Localhost
PORT = 65438        # Nport

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT)) #binding the ip and port 
    server_socket.listen(1) #server listening to connect with the client

    print("Server started. Waiting for client...") 
    conn, addr = server_socket.accept() #server accept the connection with the client
    print(f"Connected by {addr}")

    try:
        while True:
            # Receive message from client
            data = conn.recv(1024).decode()
            if not data:
                print("Client disconnected.")
                break

            print(f"Client: {data}")

            if data.lower() == "stop server":
                print("Stopping server...")
                conn.sendall("Server shutting down.".encode())
                break

            # Task 5-9: Bidirectional part: type a reply and send it back (comment out for only task 1-4)
            #reply = input("Enter reply to client: ") # Ask server user for reply
            reply = "echo"
            conn.sendall(reply.encode())
            # End of task 5-9

            if reply.lower() == "stop server":
                print("Server termination requested. Closing server.")
                break


    finally:
        conn.close()
        server_socket.close()
        print("Server terminated.")

if __name__ == "__main__":
    start_server()
