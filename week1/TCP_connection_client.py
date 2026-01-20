import socket
import sys

TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 5
msg_length = 12
quit_msg = b'quit'
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))

'''
#sending type in message, e.g. for 1-9
for line in sys.stdin:
    if 'quit_client' == line.rstrip():
        print("stopping client")
        break
    elif 'quit_server' == line.rstrip():
        print("seinding quit server msg")
        s.send(b'quit_server')
    else:
        print("sending:", line)
        s.send(line.encode('utf-8'))
        data, server_address = s.recvfrom(BUFFER_SIZE) #for task 5, for receiving server reply. Comment out for 1-4
        print(f"server response: {data.decode('utf-8')}") #also for task 5, comment out for 1-4
'''
# sending multiple messages, e.g. for 10 and 12, implementation without echo
for i in range(50):
    if i< 49:
        line = ''.join(str(i%10) for i in range(msg_length))
    elif i==49:
        line = "quit_server"
    elif i ==50:
        line = "quit_client"

    if 'quit_client' == line.rstrip():
        print("stopping client")
        break
    elif 'quit_server' == line.rstrip():
        print("seinding quit server msg")
        s.send(b'quit_server')
    else:
        print("sending:", line)
        s.send(line.encode('utf-8'))



'''
#while True:
    line = "Merry Christmas!
    s.send(line.encode('utf-8'))
    #data, server_address = s.recvfrom(BUFFER_SIZE) #for task 5, for receiving server reply. Comment out for task 12
    #print(f"server response: {data.decode('utf-8')}") #also for task 5
    '''
s.close()
#print ("received data:", data)