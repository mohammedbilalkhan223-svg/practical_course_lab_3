import paho.mqtt.client as mqtt
import sys
import time

HOSTNAME = "127.0.0.1" #of brocker
PORT = 1883
TOPIC = "demo/chat"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "publisher")
client.loop_start()
client.connect(HOSTNAME, PORT)

for line in sys.stdin:
    client.publish(TOPIC, line.rstrip())
    if 'quit' == line.rstrip():
        break
client.loop_stop()
time.sleep(1)
client.disconnect()

