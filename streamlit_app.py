"""
Dashboard CRM Wedding — dengan login & role (admin / sales).

Setup (jalankan di terminal Codespaces):
    uv add pandas openpyxl streamlit-authenticator
    uv run python load_to_sqlite.py
    uv run streamlit run streamlit_app.py

User dummy untuk login (ganti passwordnya nanti di config.yaml):
    admin / admin123   -> akses penuh, termasuk Revenue
    dewi  / sales123   -> akses terbatas, tanpa detail Revenue
"""
import sqlite3
import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

st.set_page_config(page_title="Wedding CRM Dashboard", layout="wide")

# ---------- LOGIN ----------
with open("config.yaml") as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

authenticator.login()

auth_status = st.session_state.get("authentication_status")
if auth_status is False:
    st.error("Username atau password salah")
    st.stop()
elif auth_status is None:
    st.warning("Silakan login terlebih dahulu")
    st.stop()

username = st.session_state["username"]
user_roles = config["credentials"]["usernames"][username].get("roles", ["sales"])
is_admin = "admin" in user_roles

with st.sidebar:
    st.write(f"Login sebagai **{st.session_state['name']}**")
    st.caption("Role: " + ", ".join(user_roles))
    authenticator.logout("Logout", "sidebar")

# ---------- DATA ----------
conn = sqlite3.connect("wedding_crm.db")

def load(table):
    return pd.read_sql(f"SELECT * FROM {table}", conn)

st.title("Wedding CRM Dashboard")

# tab Revenue hanya untuk admin
tab_labels = ["Ringkasan", "Profile & Keluarga", "Notifikasi"]
if is_admin:
    tab_labels.insert(2, "Event & Revenue")
tabs = st.tabs(tab_labels)
tab_map = dict(zip(tab_labels, tabs))

with tab_map["Ringkasan"]:
    accounts = load("account")
    profiles = load("profile")
    events = load("event")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total akun", len(accounts))
    col2.metric("Total event", len(events))
    if is_admin:
        revenue = load("revenue")
        col3.metric("Total revenue (Rp)", f"{revenue['amount'].sum():,.0f}")
    else:
        col3.metric("Total profile", len(profiles))

    st.subheader("Event terbaru")
    st.dataframe(events.sort_values("event_date", ascending=False), use_container_width=True)

with tab_map["Profile & Keluarga"]:
    st.subheader("Semua profile")
    profiles = load("profile")
    st.dataframe(profiles, use_container_width=True)

    st.subheader("Relasi keluarga (potensi wedding berikutnya)")
    links = load("family_link")
    merged = links.merge(profiles, on="profile_id")
    merged = merged.merge(
        profiles, left_on="related_profile_id", right_on="profile_id", suffixes=("_a", "_b")
    )
    if not merged.empty:
        display_cols = merged[["full_name_a", "relation_type", "full_name_b", "notes"]]
        display_cols.columns = ["Profile", "Hubungan", "Terhubung ke", "Catatan"]
        st.dataframe(display_cols, use_container_width=True)
    else:
        st.info("Belum ada data relasi keluarga.")

if is_admin:
    with tab_map["Event & Revenue"]:
        events = load("event")
        revenue = load("revenue")
        merged = events.merge(revenue, on="event_id", how="left")
        st.dataframe(merged, use_container_width=True)

with tab_map["Notifikasi"]:
    st.subheader("Notifikasi mendatang")
    notif = load("notification")
    profiles = load("profile")
    notif = notif.merge(profiles[["profile_id", "full_name"]], on="profile_id", how="left")
    st.dataframe(
        notif[["notif_id", "full_name", "notif_type", "trigger_date", "status"]],
        use_container_width=True,
    )
    st.caption(
        "Kolom next_occurrence/days_remaining dihitung otomatis di file Excel via formula, "
        "lalu ikut terbawa saat data disinkronkan ke database ini."
    )
