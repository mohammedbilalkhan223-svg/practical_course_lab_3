import paho.mqtt.client as mqtt
import sys

# MQTT settings
BROKER = "localhost"
PORT = 1883
TOPIC = "demo/chat"

# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Publisher connected to MQTT broker")
    else:
        print(f"❌ Connection failed with code {rc}")
        sys.exit(1)

# Create MQTT client instance
client = mqtt.Client()

# Set callbacks
client.on_connect = on_connect

# Connect to broker
try:
    client.connect(BROKER, PORT, 60)
    print("📡 Connecting to MQTT broker at localhost:1883...")

    # Start loop in background
    client.loop_start()

    print(f"✍️  Publishing to topic: {TOPIC}")
    print("Type messages and press Enter. Press Ctrl+C to exit.")

    while True:
        message = input("You: ")
        client.publish(TOPIC, message)
        print(f"📤 Published: {message}")

except KeyboardInterrupt:
    print("\n🛑 Publisher shutting down...")
except Exception as e:
    print(f"❌ Error: {e}")

finally:
    client.loop_stop()
    client.disconnect()
    print("🔌 Publisher disconnected.")