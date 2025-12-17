import socket
import sys

UDP_IP = '127.0.0.1'
UDP_PORT = 5005
BUFFER_SIZE = 40

s = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
i=0
msg_length=12



''' #msg congestion with msg spamming
while True:
    line = "hello everyone"
'''
#for line in sys.stdin: #for 1-9
 #for task 10 also change buffer size, congestion due to large msgs
for i in range(100):
    # block for task 10
    i+=1
    if i <99:
        line = ''.join(str(i%10) for i in range(msg_length)).encode('utf-8')
    elif i == 99: line= "quit_server"
    elif i == 100: line= "quit_client"

    if 'quit_client' == line.rstrip():
        print("quitting client")
        break
    elif 'quit_server' == line.rstrip():
        s.sendto(b'quit_server', (UDP_IP, UDP_PORT))
        print("quitting server")
    else:
        s.sendto(line, (UDP_IP, UDP_PORT))
        data, server_address = s.recvfrom(BUFFER_SIZE) #for task 5
        print(f"server response: {data.decode('utf-8')}")

s.close()