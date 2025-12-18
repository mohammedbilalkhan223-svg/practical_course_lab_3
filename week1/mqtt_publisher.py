import paho.mqtt.client as mqtt
import time

BROKER = "localhost"
PORT = 1883
TOPIC = "demo/chat"

def start_publisher():
    client = mqtt.Client()
    
    print(f"[STARTING] Connecting to Broker at {BROKER}...")
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start() # Start a background thread to handle network
    except Exception as e:
        print(f"[ERROR] Could not connect to broker: {e}")
        return

    print(f"[READY] Publishing to topic: {TOPIC}")
    print("Type 'stop client' to exit.")

    while True:
        msg = input("Client (you): ")
        
        # Publish message
        client.publish(TOPIC, msg)
        
        if msg.lower() == "stop client":
            break
        
        if msg.lower() == "stop server":
            # Give it a moment to send before closing
            time.sleep(0.1)
            break

    client.loop_stop()
    client.disconnect()
    print("[EXIT] Disconnected.")

if __name__ == "__main__":
    start_publisher()