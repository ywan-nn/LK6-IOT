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
MQTT_USER = "greedycat"     # GANTI DENGAN CREDENTIALS DARI LANGKAH 2
MQTT_PASSWORD = "Yuana1112" # GANTI DENGAN CREDENTIALS DARI LANGKAH 2

st.set_page_config(page_title="Smart Campus", page_icon="🏫", layout="wide")

st.title("🏫 Smart Campus Monitoring System")
st.caption(f"Monitoring Suhu & Kelembapan via HiveMQ MQTT")

# Inisialisasi MQTT client
# Gunakan blok 'try-except' yang lebih baik untuk melihat error
try:
    mqtt_client = init_mqtt_client()
    st.success("✅ MQTT Client berhasil diinisialisasi. Menunggu koneksi...")
except Exception as e:
    st.error(f"❌ Gagal menginisialisasi MQTT Client: {e}")
    st.stop()
