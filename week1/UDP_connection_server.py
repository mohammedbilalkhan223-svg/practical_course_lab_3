import socket
import random

UDP_IP = '127.0.0.1'
UDP_PORT = 5005
BUFFER_SIZE = 40 #adjust to task (1-9: larger ; 10.small e.g.4)
droprate = 0.2 #for simulating packet drop in Task 12
s = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
s.bind((UDP_IP, UDP_PORT))



while 1:
    data,add = s.recvfrom(BUFFER_SIZE)
    if data == b'quit_server':
        print("stopping now")
        break
    elif data != b'quit_client':
        s.sendto(data, add) #comment in for task 5: echo back to sender
        print("received data and replied:", data) #comment in for task 5
        pass

'''
while 1:
    data,add = s.recvfrom(BUFFER_SIZE)
    if random.random() < droprate:  ## Task 12: create random value between 0 and 1 and if smaller than droprate: drop packet
#       print(f"package drop")
    else: include for task 12
        if data == b'quit_server':
            print("stopping now")
            break
        elif data != b'quit_client':
            s.sendto(data, add)
            print("received data and replied:", data)
'''
s.close()
