import socket

TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 1024

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
except OSError:
    pass

s.bind((TCP_IP, TCP_PORT))
s.listen(1)

conn, addr = s.accept()
print ('connection address: ', addr)
while 1:
    data = conn.recv(BUFFER_SIZE)
    print ("received data:", data)
    if data == b'quit':
        print("stopping now")
        break
    #conn.send(data)
conn.close()