import streamlit as st
import paho.mqtt.client as mqtt
import pandas as pd
import plotly.express as px
import json
from datetime import datetime
from collections import deque

MQTT_BROKER = "tugasiot-03e0bc5a.a01.euc1.aws.hivemq.cloud"  # Ganti Cluster URL
MQTT_PORT = 8883
MQTT_TOPIC = "kampus/dht22"
MQTT_USER = "greedycat"     # Ganti username MQTT
MQTT_PASSWORD = "Yuana1112" # Ganti password MQTT
# ============================================================

# Inisialisasi session state
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

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        st.session_state.connected = True
        print("✅ Terhubung ke HiveMQ!")
        client.subscribe(MQTT_TOPIC)
    else:
        st.session_state.connected = False
        print(f"❌ Gagal, kode: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
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
        
        st.rerun()
    except Exception as e:
        print(f"Error: {e}")

@st.cache_resource
def init_mqtt_client():
    client = mqtt.Client(
        client_id="streamlit_dashboard",
        protocol=mqtt.MQTTv5,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1
    )
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.loop_start()
    return client

# ========== TAMPILAN DASHBOARD ==========
st.set_page_config(page_title="Smart Campus", page_icon="🏫", layout="wide")
st.title("🏫 Smart Campus Monitoring System")
st.caption("Monitoring Suhu & Kelembapan via HiveMQ MQTT")

try:
    mqtt_client = init_mqtt_client()
except Exception as e:
    st.error(f"❌ Gagal konek: {e}")

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

meter1, meter2 = st.columns(2)
with meter1:
    st.metric("🌡️ Temperature", f"{st.session_state.latest_suhu} °C")
with meter2:
    st.metric("💧 Humidity", f"{st.session_state.latest_hum} %")

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
    st.info("⏳ Belum ada data. Tunggu ESP32 mengirim data...")

st.caption("🔧 Smart Campus IoT | DHT22 → HiveMQ → Streamlit")