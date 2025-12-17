import time
import paho.mqtt.client as mqtt

BROKER = "127.0.0.1" #of brocker
PORT = 1883
TOPIC = "demo/chat"
REPLY = "reply" #for task 5


def on_message(client, userdata, message):
    print(message.topic, message.payload)
    if message.payload == b'quit':
        time.sleep(1)
        client.disconnect()
        #client.unsubscribe(TOPIC)
    elif message.payload != b'quit':
        answer = "reply" #for task 5
        client.publish(REPLY, answer.rstrip()) #for task 5
        print(f"sent {answer} on {REPLY}")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "subscriber", clean_session=True)
client.connect(BROKER, PORT)

client.on_message = on_message

client.subscribe(TOPIC)
client.loop_forever()
client.loop_stop()
