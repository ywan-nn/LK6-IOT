import streamlit as st
import paho.mqtt.client as mqtt
import pandas as pd
import plotly.express as px
import json
import ssl
import time
from datetime import datetime
from collections import deque

MQTT_BROKER = "tugasiot-03e0bc5a.a01.euc1.aws.hivemq.cloud"
MQTT_PORT = 8883  # 🔴 PAKAI 8883 BUKAN 8884
MQTT_TOPIC = "kampus/dht22"
MQTT_USER = "greedycat"
MQTT_PASSWORD = "Yuana1112"

if 'suhu_data' not in st.session_state:
    st.session_state.suhu_data = deque(maxlen=50)
if 'hum_data' not in st.session_state:
    st.session_state.hum_data = deque(maxlen=50)
if 'time_data' not in st.session_state:
    st.session_state.time_data = deque(maxlen=50)
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'latest_suhu' not in st.session_state:
    st.session_state.latest_suhu = "--"
if 'latest_hum' not in st.session_state:
    st.session_state.latest_hum = "--"
if 'mqtt_client' not in st.session_state:
    st.session_state.mqtt_client = None

def on_connect(client, userdata, flags, rc, properties=None):
    """Callback saat koneksi MQTT berhasil"""
    if rc == 0:
        st.session_state.connected = True
        print("✅ Connected to HiveMQ Cloud!")
        client.subscribe(MQTT_TOPIC)
    else:
        st.session_state.connected = False
        print(f"❌ Connection failed with code {rc}")

def on_message(client, userdata, msg):
    """Callback saat menerima pesan MQTT"""
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        
        suhu = data.get('temperature', 0)
        hum = data.get('humidity', 0)
        
        # Update session state dengan data baru
        st.session_state.latest_suhu = suhu
        st.session_state.latest_hum = hum
        st.session_state.last_update = datetime.now()
        
        st.session_state.suhu_data.append(suhu)
        st.session_state.hum_data.append(hum)
        st.session_state.time_data.append(datetime.now())
        
        print(f"📥 Received: {suhu}°C, {hum}%")
        
    except Exception as e:
        print(f"Error parsing message: {e}")

def init_mqtt_client():
    """Inisialisasi MQTT client sesuai HiveMQ official sample[citation:8]"""
    client = mqtt.Client(
        client_id="streamlit_dashboard",
        protocol=mqtt.MQTTv5  # MQTT version 5 untuk HiveMQ
    )
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Set username dan password
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    
    # 🔴 KRUSIAL: Setup TLS untuk koneksi aman
    client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    
    # Connect ke HiveMQ Cloud
    client.connect(MQTT_BROKER, MQTT_PORT)
    
    # Start loop di background
    client.loop_start()
    
    return client

# ========== TAMPILAN DASHBOARD ==========
st.set_page_config(page_title="Smart Campus", page_icon="🏫", layout="wide")

st.title("🏫 Smart Campus Monitoring System")
st.caption("Monitoring Suhu & Kelembapan via HiveMQ Cloud (MQTT over TLS)")

# Inisialisasi MQTT client (hanya sekali)
if st.session_state.mqtt_client is None:
    try:
        st.session_state.mqtt_client = init_mqtt_client()
        st.success("✅ MQTT Client initialized")
    except Exception as e:
        st.error(f"❌ Failed to initialize MQTT: {e}")

# Status Panel
col1, col2, col3 = st.columns(3)

with col1:
    if st.session_state.connected:
        st.success("🟢 MQTT Connected")
    else:
        st.error("🔴 MQTT Disconnected")
        st.caption("Waiting for connection...")

with col2:
    if st.session_state.last_update:
        st.info(f"🕐 Last Update: {st.session_state.last_update.strftime('%H:%M:%S')}")
    else:
        st.info("🕐 Waiting for data...")

with col3:
    st.info(f"📡 Topic: `{MQTT_TOPIC}`")

# Metric Cards
col_metric1, col_metric2 = st.columns(2)

with col_metric1:
    st.metric("🌡️ Temperature", f"{st.session_state.latest_suhu} °C")

with col_metric2:
    st.metric("💧 Humidity", f"{st.session_state.latest_hum} %")

# Real-time Chart
st.subheader("📈 Real-time Data History")

if len(st.session_state.time_data) > 0:
    df = pd.DataFrame({
        'Waktu': list(st.session_state.time_data),
        'Suhu (°C)': list(st.session_state.suhu_data),
        'Kelembapan (%)': list(st.session_state.hum_data)
    })
    
    fig = px.line(df, x='Waktu', y=['Suhu (°C)', 'Kelembapan (%)'])
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("📋 Recent Data")
    st.dataframe(df.tail(10).sort_values('Waktu', ascending=False))
else:
    st.info("⏳ No data yet. Waiting for ESP32 to send data...")
    st.caption("Make sure ESP32 is running and publishing to the correct topic")

# Auto-refresh every 3 seconds
st.empty()
time.sleep(3)
st.rerun()

# Footer
st.divider()
st.caption("🔧 Smart Campus IoT | DHT22 → HiveMQ Cloud → Streamlit Dashboard | MQTT over TLS (Port 8883)")
