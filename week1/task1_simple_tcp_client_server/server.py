import socket

TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 1024  # Standard buffer size

# Create socket and bind
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)

print("Server is listening on {}:{}".format(TCP_IP, TCP_PORT))

conn, addr = s.accept()
print('Connection address:', addr)

try:
    while True:
        data = conn.recv(BUFFER_SIZE)
        if not data:
            print("Client disconnected.")
            break

        message = data.decode('utf-8').strip()
        print('Received from client:', message)

        # Check for termination command
        if message.lower() == "stop client":
            print("Termination requested by client. Shutting down server...")
            break

        # Echo back the message
        conn.send(data)  # Echo back

except Exception as e:
    print("Error occurred:", e)

finally:
    conn.close()
    s.close()
    print("Server closed.")