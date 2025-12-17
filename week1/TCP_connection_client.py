import socket
import sys

TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 500
msg_length = 12
quit_msg = b'quit'
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))


''' #for task 10, also change buffer size (congestion analysis)
for i in range(50):
    if i< 49:
        line = ''.join(str(i%10) for i in range(msg_length)).encode('utf-8')
    elif i==49:
        line = "quit_server"
    elif i ==50:
        line = "quit_client"
'''
''' #congestion with msg spamming 
while True:
    line = "Merry christmas!"'''
for line in sys.stdin: #Task 1-9


    if 'quit_client' == line.rstrip():
        print("stopping client")
        break
    elif 'quit_server' == line.rstrip():
        s.send(b'quit_server')
    else:
        print("sending:", line)
        s.send(line)
        data, server_address = s.recvfrom(BUFFER_SIZE) #for task 5
        print(f"server response: {data.decode('utf-8')}")

s.close()
#print ("received data:", data)