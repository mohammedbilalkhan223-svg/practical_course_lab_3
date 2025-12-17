import socket

TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 500

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1) #allows to reuse the socket


s.bind((TCP_IP, TCP_PORT))
s.listen(1)

conn, addr = s.accept()
print ('connection address: ', addr)
while 1:
    data, addr = conn.recvfrom(BUFFER_SIZE)
    print ("received data:", data)
    if data == b'quit_server':
        print("stopping now")
        break
    elif data == b'':
        break
    elif data != b'quit_client':
        conn.send(data) #for task 5
        print("send reply")

s.close()
conn.close()
