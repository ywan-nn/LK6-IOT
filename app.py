import streamlit as st
import paho.mqtt.client as mqtt
import pandas as pd
import plotly.express as px
import json
import ssl
from datetime import datetime
from collections import deque

MQTT_BROKER = "tugasiot-03e0bc5a.a01.euc1.aws.hivemq.cloud"
MQTT_PORT = 8884
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

def on_connect(client, userdata, flags, rc):
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
        print(f"Error parsing message: {e}")

@st.cache_resource
def init_mqtt_client():
    # Buat MQTT client
    client = mqtt.Client(
        client_id="streamlit_dashboard",
        protocol=mqtt.MQTTv5
    )
    
    # Set username dan password
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    
    # Setup TLS untuk HiveMQ Cloud
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
    
    # Set callback functions
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Connect ke broker
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    
    # Start loop background
    client.loop_start()
    
    return client

# ========== TAMPILAN DASHBOARD ==========
st.set_page_config(page_title="Smart Campus", page_icon="🏫", layout="wide")

st.title("🏫 Smart Campus Monitoring System")
st.caption("Monitoring Suhu & Kelembapan via HiveMQ MQTT")

# Inisialisasi MQTT client
try:
    mqtt_client = init_mqtt_client()
    st.success("✅ MQTT Client berhasil diinisialisasi. Menunggu koneksi...")
except Exception as e:
    st.error(f"❌ Gagal menginisialisasi MQTT Client: {e}")
    st.stop()

# Status Panel
col1, col2, col3 = st.columns(3)

with col1:
    if st.session_state.connected:
        st.success("🟢 MQTT Connected")
    else:
        st.error("🔴 MQTT Disconnected")
        st.caption("Menunggu koneksi...")

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
    st.metric(
        label="🌡️ Temperature",
        value=f"{st.session_state.latest_suhu} °C",
        delta=None if st.session_state.latest_suhu == "--" else None
    )

with col_metric2:
    st.metric(
        label="💧 Humidity",
        value=f"{st.session_state.latest_hum} %",
        delta=None if st.session_state.latest_hum == "--" else None
    )

# Real-time Chart
st.subheader("📈 Real-time Data History")

if len(st.session_state.time_data) > 0:
    df = pd.DataFrame({
        'Waktu': list(st.session_state.time_data),
        'Suhu (°C)': list(st.session_state.suhu_data),
        'Kelembapan (%)': list(st.session_state.hum_data)
    })
    
    fig = px.line(
        df, 
        x='Waktu', 
        y=['Suhu (°C)', 'Kelembapan (%)'],
        title='Sensor Reading History',
        labels={'value': 'Nilai', 'variable': 'Parameter', 'Waktu': 'Waktu'},
        color_discrete_map={'Suhu (°C)': '#ff4b4b', 'Kelembapan (%)': '#4b9eff'}
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Data Table
    st.subheader("📋 Recent Data")
    st.dataframe(
        df.tail(10).sort_values('Waktu', ascending=False),
        use_container_width=True,
        column_config={
            "Waktu": st.column_config.DatetimeColumn("Waktu", format="HH:mm:ss"),
            "Suhu (°C)": st.column_config.NumberColumn("Suhu", format="%.1f °C"),
            "Kelembapan (%)": st.column_config.NumberColumn("Kelembapan", format="%.1f %%")
        }
    )
else:
    st.info("⏳ Belum ada data. Tunggu ESP32 mengirim data ke MQTT...")
    st.caption("Pastikan ESP32 sudah terhubung dan mengirim data ke topic yang sama")

# Footer
st.divider()
st.caption("🔧 Smart Campus IoT System | DHT22 → HiveMQ → Streamlit Dashboard")
