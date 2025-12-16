import socket

UDP_IP = '127.0.0.1'
UDP_PORT = 5005
BUFFER_SIZE = 1024

s = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

s.bind((UDP_IP, UDP_PORT))

while 1:
    data = s.recv(BUFFER_SIZE)
    print ("received data:", data)
    if data == b'quit':
        print("stopping now")
        break
    #conn.send(data)
