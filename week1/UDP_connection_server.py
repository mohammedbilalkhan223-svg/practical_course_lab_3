import socket

UDP_IP = '127.0.0.1'
UDP_PORT = 5005
BUFFER_SIZE = 4

s = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

s.bind((UDP_IP, UDP_PORT))

while 1:
    data,add = s.recvfrom(BUFFER_SIZE)
    if data == b'quit_server':
        print("stopping now")
        break
    elif data != b'quit_client':
        s.sendto(data, add)
        print("received data and replied:", data)
    #conn.send(data)
s.close()
