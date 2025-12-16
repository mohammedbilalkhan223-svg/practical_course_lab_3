import time
import paho.mqtt.client as mqtt

HOSTNAME = "127.0.0.1" #of brocker
PORT = 1883
TOPIC = "demo/chat"



def on_message(client, userdata, message):
    print(message.topic, message.payload)
    if message.payload == b'quit':
        client.unsubscribe(TOPIC)


def on_unsubscribe(client, userdata, message, reason_code_list, properties):
    client.disconnect(TOPIC)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "subscriber")
client.on_message = on_message
client.on_unsubscribe = on_unsubscribe
client.connect(HOSTNAME, PORT)
client.subscribe(TOPIC)
client.loop_forever()
client.loop_stop()
