"""
Dashboard CRM Wedding — versi awal, jalan 100% offline di PC.

Cara pakai:
    1. pip install streamlit pandas
    2. python load_to_sqlite.py      (sekali di awal, atau tiap update data)
    3. streamlit run dashboard.py    (buka otomatis di browser lokal)

Nanti kalau mau online: deploy folder ini ke Streamlit Community Cloud (gratis),
kode ini tidak perlu diubah. Karena berbasis browser, otomatis bisa dibuka dari HP.
"""
import sqlite3
import pandas as pd
import streamlit as st
from datetime import date

st.set_page_config(page_title="Wedding CRM Dashboard", layout="wide")

conn = sqlite3.connect("wedding_crm.db")

def load(table):
    return pd.read_sql(f"SELECT * FROM {table}", conn)

st.title("Wedding CRM Dashboard")

tab1, tab2, tab3, tab4 = st.tabs(["Ringkasan", "Profile & Keluarga", "Event & Revenue", "Notifikasi"])

with tab1:
    accounts = load("account")
    profiles = load("profile")
    events = load("event")
    revenue = load("revenue")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total akun", len(accounts))
    col2.metric("Total event", len(events))
    col3.metric("Total revenue (Rp)", f"{revenue['amount'].sum():,.0f}")

    st.subheader("Event terbaru")
    st.dataframe(events.sort_values("event_date", ascending=False), use_container_width=True)

with tab2:
    st.subheader("Semua profile")
    profiles = load("profile")
    st.dataframe(profiles, use_container_width=True)

    st.subheader("Relasi keluarga (potensi wedding berikutnya)")
    links = load("family_link")
    merged = links.merge(profiles, left_on="profile_id", right_on="profile_id", suffixes=("", "_a"))
    merged = merged.merge(
        profiles, left_on="related_profile_id", right_on="profile_id", suffixes=("_a", "_b")
    )
    if not merged.empty:
        display_cols = merged[["full_name_a", "relation_type", "full_name_b", "notes"]]
        display_cols.columns = ["Profile", "Hubungan", "Terhubung ke", "Catatan"]
        st.dataframe(display_cols, use_container_width=True)
    else:
        st.info("Belum ada data relasi keluarga.")

with tab3:
    events = load("event")
    revenue = load("revenue")
    merged = events.merge(revenue, on="event_id", how="left")
    st.dataframe(merged, use_container_width=True)

with tab4:
    st.subheader("Notifikasi mendatang")
    notif = load("notification")
    profiles = load("profile")
    notif = notif.merge(profiles[["profile_id", "full_name"]], on="profile_id", how="left")
    notif["trigger_date"] = pd.to_datetime(notif["trigger_date"], errors="coerce")
    notif["days_remaining"] = (notif["next_occurrence"].apply(pd.to_datetime, errors="coerce"))
    notif = notif.sort_values("trigger_date")
    st.dataframe(
        notif[["notif_id", "full_name", "notif_type", "trigger_date", "status"]],
        use_container_width=True,
    )
    st.caption(
        "Catatan: kolom next_occurrence/days_remaining dihitung otomatis di Excel via formula. "
        "Setelah data disinkronkan dari Excel yang sudah di-recalculate, nilainya akan ikut terbawa."
    )
