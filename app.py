import streamlit as st
import paho.mqtt.client as mqtt
import pandas as pd
import plotly.express as px
import json
import ssl
import queue
import time
from datetime import datetime
from collections import deque

# ============================================================
# GANTI DENGAN DATA HIVEMQ KAMU
# ============================================================
MQTT_BROKER = "tugasiot-03e0bc5a.a01.euc1.aws.hivemq.cloud"
MQTT_PORT = 8883
MQTT_TOPIC = "kampus/dht22"
MQTT_USER = "greedycat"
MQTT_PASSWORD = "Yuana1112"
# ============================================================

# Session state untuk menyimpan data
if 'suhu_data' not in st.session_state:
    st.session_state.suhu_data = deque(maxlen=50)
    st.session_state.hum_data = deque(maxlen=50)
    st.session_state.time_data = deque(maxlen=50)
    st.session_state.last_update = None
    st.session_state.connected = False
    st.session_state.latest_suhu = "--"
    st.session_state.latest_hum = "--"

# Queue untuk komunikasi antar thread
message_queue = queue.Queue()

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        st.session_state.connected = True
        print("✅ Terhubung ke HiveMQ!")
        client.subscribe(MQTT_TOPIC)
    else:
        st.session_state.connected = False
        print(f"❌ Gagal terhubung, kode: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        message_queue.put(payload)
    except Exception as e:
        print(f"Error: {e}")

@st.cache_resource
def init_mqtt_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()
    return client

# ========== TAMPILAN DASHBOARD ==========
st.set_page_config(page_title="Smart Campus", page_icon="🏫", layout="wide")

st.title("🏫 Smart Campus Monitoring System")
st.caption("Monitoring Suhu & Kelembapan via HiveMQ MQTT")

# Inisialisasi MQTT
try:
    mqtt_client = init_mqtt_client()
    st.success("✅ MQTT Client berjalan")
except Exception as e:
    st.error(f"❌ Gagal: {e}")
    st.stop()

# Proses data dari queue
while not message_queue.empty():
    try:
        payload = message_queue.get_nowait()
        data = json.loads(payload)
        
        suhu = data.get('temperature', 0)
        hum = data.get('humidity', 0)
        now = datetime.now()
        
        st.session_state.latest_suhu = suhu
        st.session_state.latest_hum = hum
        st.session_state.last_update = now
        
        st.session_state.suhu_data.append(suhu)
        st.session_state.hum_data.append(hum)
        st.session_state.time_data.append(now)
    except Exception as e:
        print(f"Error proses: {e}")

# Status panel
col1, col2, col3 = st.columns(3)
with col1:
    if st.session_state.connected:
        st.success("🟢 MQTT Connected")
    else:
        st.error("🔴 MQTT Disconnected")
with col2:
    if st.session_state.last_update:
        st.info(f"🕐 Update: {st.session_state.last_update.strftime('%H:%M:%S')}")
    else:
        st.info("🕐 Menunggu data...")
with col3:
    st.info(f"📡 Topic: {MQTT_TOPIC}")

# Metric cards
col_m1, col_m2 = st.columns(2)
with col_m1:
    st.metric("🌡️ Temperature", f"{st.session_state.latest_suhu} °C")
with col_m2:
    st.metric("💧 Humidity", f"{st.session_state.latest_hum} %")

# Grafik
st.subheader("📈 Grafik Real-time")
if len(st.session_state.time_data) > 0:
    df = pd.DataFrame({
        'Waktu': list(st.session_state.time_data),
        'Suhu (°C)': list(st.session_state.suhu_data),
        'Kelembapan (%)': list(st.session_state.hum_data)
    })
    fig = px.line(df, x='Waktu', y=['Suhu (°C)', 'Kelembapan (%)'])
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("📋 Data Terbaru")
    st.dataframe(df.tail(10).sort_values('Waktu', ascending=False))
else:
    st.info("⏳ Belum ada data. Tunggu ESP32 mengirim...")

# Auto refresh
time.sleep(2)
st.rerun()
