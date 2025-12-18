import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "demo/chat"

# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[CONNECTED] Connected to MQTT Broker!")
        # Subscribe to the topic upon successful connection
        client.subscribe(TOPIC)
        print(f"[SUBSCRIBED] Listening on topic: {TOPIC}")
    else:
        print(f"[ERROR] Failed to connect, return code {rc}")

# Callback when a message is received
def on_message(client, userdata, msg):
    message = msg.payload.decode()
    print(f"[RECEIVED] Topic: {msg.topic} | Message: {message}")
    
    if message.lower() == "stop server":
        print("[STOP] Stop command received. Disconnecting...")
        client.disconnect()

def start_subscriber():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[STARTING] Connecting to Broker at {BROKER}...")
    client.connect(BROKER, PORT, 60)

    # loop_forever handles network traffic, dispatching callbacks, and reconnection
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("[EXIT] Disconnecting...")
        client.disconnect()

if __name__ == "__main__":
    start_subscriber()