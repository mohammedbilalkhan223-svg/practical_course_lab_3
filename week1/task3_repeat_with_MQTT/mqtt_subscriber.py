import paho.mqtt.client as mqtt

# MQTT settings
BROKER = "localhost"
PORT = 1883
TOPIC = "demo/chat"

# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Subscriber connected to MQTT broker")
        client.subscribe(TOPIC)
        print(f"👂 Listening on topic: {TOPIC}")
    else:
        print(f"❌ Connection failed with code {rc}")

# Callback when a message is received
def on_message(client, userdata, msg):
    print(f"📩 Received on {msg.topic}: {msg.payload.decode('utf-8')}")

# Create MQTT client instance
client = mqtt.Client()

# Set callbacks
client.on_connect = on_connect
client.on_message = on_message

# Connect to broker
try:
    client.connect(BROKER, PORT, 60)
    print("📡 Connecting to MQTT broker at localhost:1883...")
    
    # Start the loop to process messages
    client.loop_forever()

except KeyboardInterrupt:
    print("\n🛑 Subscriber shutting down...")
except Exception as e:
    print(f"❌ Error: {e}")

finally:
    client.disconnect()
    print("🔌 Subscriber disconnected.")