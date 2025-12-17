import socket
import random

TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 20 #adjust for congestion analysis
droprate = 0.2 #for task 12 simulating package drop

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1) #allows to reuse the socket
s.bind((TCP_IP, TCP_PORT))
s.listen(1)
conn, addr = s.accept()
print ('connection address: ', addr)
'''
# Task 1-11
while 1:
    data, addr = conn.recvfrom(BUFFER_SIZE)
    print ("received data:", data)
    if data == b'quit_server':
        print("stopping now")
        break
    elif data==b'quit_client':
        print("client quitting before server")
    elif data == b'':
        break
    elif data != b'quit_client':
        print("send reply with ", data) # Task 5: sending echo to sender, keep in if you want echo
        conn.send(data) # Task 5
        pass
'''        
# Task 12
while 1:
    data, addr = conn.recvfrom(BUFFER_SIZE)
    # add part for task 12 here and shift in part after for the else:
    if random.random() < droprate:  ## Task 12: create random value between 0 and 1 and if smaller than droprate: drop packet
        print(f"package drop")
        pass
    else:  # otherwise handle the message
        print ("received data:", data)
        if data == b'quit_server':
            print("stopping now")
            break
        elif data==b'quit_client':
            print("client quitting before server")
        elif data == b'':
            break
        elif data != b'quit_client':
            pass


s.close()
conn.close()
