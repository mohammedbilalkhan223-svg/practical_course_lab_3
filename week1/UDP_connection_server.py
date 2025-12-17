import socket
import random

UDP_IP = '127.0.0.1'
UDP_PORT = 5005
BUFFER_SIZE = 40 #adjust to task (1-9: larger ; 10.small e.g.4)
droprate = 0.2 #for simulating packet drop in Task 12
s = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
s.bind((UDP_IP, UDP_PORT))

''' #This block is needed for task 12, add after s.recvfrom(BUFFER_SIZE)
# if random.random() < droprate:  ## Task 12: create random value between 0 and 1 and if smaller than droprate: drop packet
#    print(f"package drop")
'''

while 1:
    data,add = s.recvfrom(BUFFER_SIZE)
    # include block for task 12
    #else: include for task 12
    if data == b'quit_server':
        print("stopping now")
        break
    elif data != b'quit_client':
        s.sendto(data, add)
        print("received data and replied:", data)
    #conn.send(data)
s.close()
