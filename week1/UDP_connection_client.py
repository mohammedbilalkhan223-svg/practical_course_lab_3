import socket
import sys

UDP_IP = '127.0.0.1'
UDP_PORT = 5005
BUFFER_SIZE = 40 #adjust to task (1-9: larger ; 10.small e.g.4)

s = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
#Blocks for the different tasks
# **Task 1-9**
for line in sys.stdin: #This is task 1-9
    if 'quit_client' == line.rstrip():
        print("quitting client")
        break
    elif 'quit_server' == line.rstrip():
        s.sendto(b'quit_server', (UDP_IP, UDP_PORT))
        print("quitting server")
    else:
        s.sendto(line.encode('utf-8'), (UDP_IP, UDP_PORT))
        print("seinding msg", line)
        data, server_address = s.recvfrom(BUFFER_SIZE) #for task 5, for waiting for server reply. Comment out for 1-4
        print(f"server response: {data.decode('utf-8')}") #for Task 5, comment out for 1-4



'''# **Task 10** also change buffer size, no echo implementation
i=0 #this is task 10
msg_length=12
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
        s.sendto(line.encode('utf-8'), (UDP_IP, UDP_PORT))
        print("seinding msg", line)

'''

''' #Task 10, trying msg spamming (endless msg spam)
while True:
    line = "hello everyone"
    s.sendto(line.encode('utf-8'), (UDP_IP, UDP_PORT))
    print("seinding msg", line)
'''

