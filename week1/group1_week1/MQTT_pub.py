import paho.mqtt.client as mqtt
import sys
import time

BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "demo/chat"
REPLY = "reply" #for task 5

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "publisher", clean_session=True)

client.connect(BROKER, PORT)
client.subscribe(REPLY) #for task 5

def on_message(client, userdata, message): #for task 5
    print("message received", message.topic, message.payload)

client.on_message = on_message #for task 5
client.loop_start()
for line in sys.stdin:
    client.publish(TOPIC, line.rstrip())
    if 'quit' == line.rstrip():
        client.loop_stop()
        time.sleep(1)
        break

client.disconnect()

