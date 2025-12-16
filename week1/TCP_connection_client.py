import socket
import sys

TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 1024
#MESSAGE = b'Hello World!'

quit_msg = b'quit'
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))
#s.send(MESSAGE)
#data = s.recv(BUFFER_SIZE)
for line in sys.stdin:
    if 'quit' == line.rstrip():
        s.send(quit_msg)
        break
    else:
        s.send(line.encode('utf-8'))

s.close()
#print ("received data:", data)