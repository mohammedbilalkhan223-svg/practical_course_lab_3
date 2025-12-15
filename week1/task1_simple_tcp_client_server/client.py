import socket

TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 1024

# Create socket and connect
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))

print("Connected to server at {}:{}".format(TCP_IP, TCP_PORT))
print("Type messages to send. Type 'stop client' to terminate the connection.")

try:
    while True:
        # Get input from user
        message = input("You: ")

        # Send message to server
        s.send(message.encode('utf-8'))

        # Check if client wants to stop
        if message.lower() == "stop client":
            print("Termination message sent. Closing connection...")
            break

        # Receive echo from server
        data = s.recv(BUFFER_SIZE)
        if not data:
            print("Server disconnected.")
            break

        print("Server:", data.decode('utf-8'))

except Exception as e:
    print("Error occurred:", e)

finally:
    s.close()
    print("Client closed.")