import streamlit as st
import paho.mqtt.client as mqtt
import pandas as pd
import plotly.express as px
import jsonimport streamlit as st
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
# 1. GANTI INI PAKAI DATA HIVEMQ KAMU
# ============================================================
MQTT_BROKER = "tugasiot-03e0bc5a.a01.euc1.aws.hivemq.cloud"   # GANTI
MQTT_PORT = 8883
MQTT_TOPIC = "kampus/dht22"                                   # GANTI
MQTT_USER = "greedycat"                                       # GANTI
MQTT_PASSWORD = "Yuana1112"                                   # GANTI
# ============================================================

# --- BIKIN WADAH DATA DI SESSION STATE ---
if 'suhu_data' not in st.session_state:
    st.session_state.suhu_data = deque(maxlen=50)
    st.session_state.hum_data = deque(maxlen=50)
    st.session_state.time_data = deque(maxlen=50)
    st.session_state.last_update = None
    st.session_state.connected = False
    st.session_state.latest_suhu = "--"
    st.session_state.latest_hum = "--"

# --- INI PENTING: QUEUE BUAT NAMPUNG DATA DARI THREAD MQTT ---
message_queue = queue.Queue()

# --- FUNGSI CALLBACK MQTT (Cuma taruh data di queue) ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        st.session_state.connected = True
        print("✅ Koneksi Berhasil!")
        client.subscribe(MQTT_TOPIC)
    else:
        st.session_state.connected = False
        print(f"❌ Gagal Konek, kode: {rc}")

def on_message(client, userdata, msg):
    """INI LOOP YANG DIJALANKAN DI THREAD LAIN. Cuma masukkan data ke queue."""
    try:
        payload = msg.payload.decode()
        message_queue.put(payload)  # <-- Data masuk ke antrian
    except Exception as e:
        print(f"Error di MQTT: {e}")

@st.cache_resource
def init_mqtt_client():
    """Jalankan MQTT di background (cuma diinisialisasi sekali)."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5)
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)  # <-- Wajib buat HiveMQ
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_start()  # <-- Jalanin loop di background, biar gak nge-blok Streamlit
    return client

# --- TAMPILAN WEBSITE ---
st.set_page_config(page_title="Smart Campus", page_icon="🏫", layout="wide")
st.title("🏫 Smart Campus Monitoring System")
st.caption("Monitoring Suhu & Kelembapan via HiveMQ (MQTT over TLS)")

# Panggil fungsi MQTT (cuma sekali)
try:
    mqtt_client = init_mqtt_client()
    st.success("✅ Client MQTT berjalan")
except Exception as e:
    st.error(f"❌ Gagal: {e}")
    st.stop()

# --- PROSES DATA DARI QUEUE (INI KUNCI BIAR DASHBOARD UPDATE) ---
# Kode ini jalan setiap kali Streamlit me-refresh halaman (beberapa kali per detik)
while not message_queue.empty():
    try:
        payload = message_queue.get_nowait()
        data = json.loads(payload)
        
        suhu = data.get('temperature', 0)
        hum = data.get('humidity', 0)
        now = datetime.now()
        
        # Update session state dengan data terbaru
        st.session_state.latest_suhu = suhu
        st.session_state.latest_hum = hum
        st.session_state.last_update = now
        
        st.session_state.suhu_data.append(suhu)
        st.session_state.hum_data.append(hum)
        st.session_state.time_data.append(now)
        
        print(f"📥 Data diproses: {suhu}°C, {hum}%")
    except Exception as e:
        print(f"Error proses data: {e}")

# --- PANEL STATUS ---
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
    st.info(f"📡 Topic: `{MQTT_TOPIC}`")

# --- METRIC CARD ---
col_m1, col_m2 = st.columns(2)
with col_m1:
    st.metric("🌡️ Temperature", f"{st.session_state.latest_suhu} °C")
with col_m2:
    st.metric("💧 Kelembapan", f"{st.session_state.latest_hum} %")

# --- GRAFIK & TABEL ---
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

# --- AUTO REFRESH (Biar ambil data dari queue terus) ---
time.sleep(2)
st.rerun()
import ssl
import queue
import time
from datetime import datetime
from collections import deque

# ============================================================
# 1. KONFIGURASI (GANTI DENGAN PUNYA ANDA)
# ============================================================
MQTT_BROKER = "tugasiot-03e0bc5a.a01.euc1.aws.hivemq.cloud"
MQTT_PORT = 8883  # Port 8883 untuk koneksi MQTT lewat TLS
MQTT_TOPIC = "kampus/dht22"
MQTT_USER = "greedycat"     # Username MQTT kamu
MQTT_PASSWORD = "Yuana1112" # Password MQTT kamu
# ============================================================

# --- Bagian untuk Menampung Data ---
if 'suhu_data' not in st.session_state:
    st.session_state.suhu_data = deque(maxlen=50)
    st.session_state.hum_data = deque(maxlen=50)
    st.session_state.time_data = deque(maxlen=50)
    st.session_state.last_update = None
    st.session_state.connected = False
    st.session_state.latest_suhu = "--"
    st.session_state.latest_hum = "--"

# Queue untuk komunikasi antar thread (wajib agar data bisa masuk ke dashboard)
message_queue = queue.Queue()

# --- Fungsi Callback MQTT ---
def on_connect(client, userdata, flags, rc, properties=None):
    """Dipanggil saat mencoba konek ke broker."""
    if rc == 0:
        st.session_state.connected = True
        print("✅ Berhasil terhubung ke HiveMQ Cloud!")
        client.subscribe(MQTT_TOPIC) # Subscribe ke topic
    else:
        st.session_state.connected = False
        print(f"❌ Gagal terhubung, kode error: {rc}")

def on_message(client, userdata, msg):
    """Dipanggil saat ada pesan masuk. Kita masukkan ke queue."""
    try:
        payload = msg.payload.decode()
        # Langsung masukkan payload mentah ke queue
        message_queue.put(payload)
    except Exception as e:
        print(f"Error di callback on_message: {e}")

@st.cache_resource
def init_mqtt_client():
    """Membuat dan mengkonfigurasi MQTT Client."""
    # Gunakan versi callback API terbaru
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    
    # Set username dan password
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    
    # *** PERBAIKAN UTAMA ada di SINI ***
    # Hanya panggil tls_set() tanpa parameter untuk menggunakan default TLS yang aman
    # Metode ini sudah direkomendasikan oleh dokumentasi Paho MQTT.
    client.tls_set()
    
    # Pasang fungsi callback
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Coba konek ke broker
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    
    # Jalankan loop MQTT di background
    client.loop_start()
    
    return client

# ========== MEMBUAT TAMPILAN WEBSITE (UI) ==========
st.set_page_config(page_title="Smart Campus", page_icon="🏫", layout="wide")
st.title("🏫 Smart Campus Monitoring System")
st.caption("Menampilkan data Suhu & Kelembapan dari sensor DHT22 secara Real-time")

# Panggil fungsi untuk memulai koneksi MQTT
try:
    mqtt_client = init_mqtt_client()
    st.success("✅ Client MQTT berhasil diinisialisasi.")
except Exception as e:
    st.error(f"❌ Gagal menginisialisasi MQTT: {e}")
    st.stop()

# --- Proses Data dari Queue (Kunci Dashboard Bisa Jalan) ---
try:
    # Loop selama ada antrian pesan yang belum diproses
    while not message_queue.empty():
        payload = message_queue.get_nowait()
        data = json.loads(payload)
        
        # Ekstrak data suhu dan kelembapan
        suhu = data.get('temperature', 0)
        hum = data.get('humidity', 0)
        now = datetime.now()
        
        # Update session state
        st.session_state.latest_suhu = suhu
        st.session_state.latest_hum = hum
        st.session_state.last_update = now
        
        st.session_state.suhu_data.append(suhu)
        st.session_state.hum_data.append(hum)
        st.session_state.time_data.append(now)
        
        print(f"📥 Data masuk: {suhu}°C, {hum}%")
        
except queue.Empty:
    pass
except Exception as e:
    st.error(f"Error memproses data: {e}")

# --- Menampilkan Status Koneksi dan Data ---
col1, col2, col3 = st.columns(3)
with col1:
    if st.session_state.connected:
        st.success("🟢 STATUS: Terhubung ke MQTT")
    else:
        st.error("🔴 STATUS: Terputus")
with col2:
    if st.session_state.last_update:
        st.info(f"🕐 Update Terakhir: {st.session_state.last_update.strftime('%H:%M:%S')}")
    else:
        st.info("🕐 Menunggu data dari ESP32...")
with col3:
    st.info(f"📡 Topic: `{MQTT_TOPIC}`")

# Menampilkan nilai terbaru dalam bentuk kartu besar
col_metric1, col_metric2 = st.columns(2)
with col_metric1:
    st.metric("🌡️ SUHU RUANGAN", f"{st.session_state.latest_suhu} °C")
with col_metric2:
    st.metric("💧 KELEMBAPAN", f"{st.session_state.latest_hum} %")

# --- Menampilkan Grafik dan Tabel ---
st.subheader("📈 GRAFIK PERUBAHAN DATA")
if len(st.session_state.time_data) > 0:
    df = pd.DataFrame({
        'Waktu': list(st.session_state.time_data),
        'Suhu (°C)': list(st.session_state.suhu_data),
        'Kelembapan (%)': list(st.session_state.hum_data)
    })
    
    fig = px.line(df, x='Waktu', y=['Suhu (°C)', 'Kelembapan (%)'])
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("📋 10 DATA TERBARU")
    st.dataframe(df.tail(10).sort_values('Waktu', ascending=False))
else:
    st.info("⏳ Belum ada data yang masuk. Pastikan ESP32 sudah mengirim.")

# Otomatis refresh halaman setiap 3 detik
time.sleep(3)
st.rerun()
