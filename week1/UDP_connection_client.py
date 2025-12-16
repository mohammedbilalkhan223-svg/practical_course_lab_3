import socket
import sys

UDP_IP = '127.0.0.1'
UDP_PORT = 5005
BUFFER_SIZE = 1024

s = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)



for line in sys.stdin:
    if 'quit' == line.rstrip():
        s.sendto(b'quit', (UDP_IP, UDP_PORT))
        break
    else:
        s.sendto(line.encode('utf-8'), (UDP_IP, UDP_PORT))

