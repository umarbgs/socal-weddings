"""
Dashboard CRM Wedding — login & role, input data langsung dari dashboard,
grafik revenue, dan notifikasi (anniversary/birthday/custom).

Setup (jalankan di terminal Codespaces):
    uv add pandas openpyxl streamlit-authenticator
    uv run python load_to_sqlite.py   (sekali saja, untuk isi data awal dari Excel)
    uv run streamlit run streamlit_app.py

Setelah ini jalan, SEMUA data baru cukup diinput lewat tab "Input Data" —
tidak perlu buka Excel lagi. Excel/load_to_sqlite.py hanya dipakai sekali
di awal untuk isi data dummy.

User dummy untuk login (ganti passwordnya nanti di config.yaml):
    admin / admin123   -> akses penuh, termasuk Revenue
    dewi  / sales123   -> akses terbatas, tanpa detail Revenue
"""
import sqlite3
from datetime import date

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

# ---------- DATABASE ----------
conn = sqlite3.connect("wedding_crm.db", check_same_thread=False)

def load(table):
    return pd.read_sql(f"SELECT * FROM {table}", conn)

def next_id(table, id_col, prefix):
    """Generate ID berikutnya, mis. PRF-0007, dengan cari angka terbesar yang sudah ada."""
    df = load(table)
    if df.empty:
        return f"{prefix}-0001"
    nums = df[id_col].str.extract(r"(\d+)$")[0].astype(int)
    return f"{prefix}-{nums.max() + 1:04d}"

def run_insert(sql, params):
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()

def compute_next_occurrence(trigger_date_str):
    """Pengganti formula Excel: hitung tanggal ulang terdekat dari hari ini."""
    if not trigger_date_str:
        return None, None
    try:
        d = pd.to_datetime(trigger_date_str).date()
    except Exception:
        return None, None
    today = date.today()
    candidate = date(today.year, d.month, d.day)
    if candidate < today:
        candidate = date(today.year + 1, d.month, d.day)
    return candidate, (candidate - today).days

st.title("Wedding CRM Dashboard")

tab_labels = ["Ringkasan", "Profile & Keluarga", "Notifikasi", "Input Data"]
if is_admin:
    tab_labels.insert(2, "Event & Revenue")
tabs = st.tabs(tab_labels)
tab_map = dict(zip(tab_labels, tabs))

# ============================================================
# RINGKASAN
# ============================================================
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

    if is_admin and not events.empty:
        st.subheader("Revenue per bulan")
        rev = load("revenue")
        ev = load("event")[["event_id", "event_date"]]
        merged = rev.merge(ev, on="event_id", how="left")
        merged["event_date"] = pd.to_datetime(merged["event_date"])
        merged["bulan"] = merged["event_date"].dt.to_period("M").astype(str)
        chart_data = merged.groupby("bulan")["amount"].sum()
        st.bar_chart(chart_data)

        st.subheader("Jumlah event per tipe")
        st.bar_chart(events["event_type"].value_counts())

    st.subheader("Event terbaru")
    st.dataframe(events.sort_values("event_date", ascending=False), use_container_width=True)

# ============================================================
# PROFILE & KELUARGA
# ============================================================
with tab_map["Profile & Keluarga"]:
    st.subheader("Semua profile")
    profiles = load("profile")
    st.dataframe(profiles, use_container_width=True)

    st.subheader("Relasi keluarga (potensi wedding berikutnya)")
    links = load("family_link")
    if not links.empty:
        merged = links.merge(profiles, on="profile_id")
        merged = merged.merge(
            profiles, left_on="related_profile_id", right_on="profile_id", suffixes=("_a", "_b")
        )
        display_cols = merged[["full_name_a", "relation_type", "full_name_b", "notes"]]
        display_cols.columns = ["Profile", "Hubungan", "Terhubung ke", "Catatan"]
        st.dataframe(display_cols, use_container_width=True)
    else:
        st.info("Belum ada data relasi keluarga.")

# ============================================================
# EVENT & REVENUE (admin only)
# ============================================================
if is_admin:
    with tab_map["Event & Revenue"]:
        events = load("event")
        revenue = load("revenue")
        merged = events.merge(revenue, on="event_id", how="left")
        st.dataframe(merged, use_container_width=True)

# ============================================================
# NOTIFIKASI
# ============================================================
with tab_map["Notifikasi"]:
    st.subheader("Notifikasi mendatang")
    notif = load("notification")
    profiles = load("profile")
    events = load("event")

    if not notif.empty:
        notif = notif.merge(profiles[["profile_id", "full_name"]], on="profile_id", how="left")

        trigger_dates = []
        for _, row in notif.iterrows():
            if row["notif_type"] == "wedding_anniversary" and pd.notna(row.get("event_id")):
                ev_row = events[events["event_id"] == row["event_id"]]
                trigger_dates.append(ev_row["event_date"].values[0] if not ev_row.empty else row.get("trigger_date"))
            elif row["notif_type"] == "birthday":
                pr_row = profiles[profiles["profile_id"] == row["profile_id"]]
                trigger_dates.append(pr_row["birthdate"].values[0] if not pr_row.empty else row.get("trigger_date"))
            else:
                trigger_dates.append(row.get("trigger_date"))
        notif["trigger_date"] = trigger_dates

        next_occ, days_left = zip(*notif["trigger_date"].apply(compute_next_occurrence))
        notif["next_occurrence"] = next_occ
        notif["days_remaining"] = days_left
        notif = notif.sort_values("days_remaining")

        st.dataframe(
            notif[["full_name", "notif_type", "next_occurrence", "days_remaining", "status"]],
            use_container_width=True,
        )
    else:
        st.info("Belum ada notifikasi.")

# ============================================================
# INPUT DATA
# ============================================================
with tab_map["Input Data"]:
    st.caption("Semua input di sini langsung tersimpan ke database — tidak perlu Excel lagi.")
    input_tabs = st.tabs(["Profile Baru", "Relasi Keluarga", "Event Baru", "Revenue", "Notifikasi Custom"])

    # --- Profile baru ---
    with input_tabs[0]:
        accounts = load("account")
        account_options = accounts["account_id"].tolist() if not accounts.empty else []
        with st.form("form_profile"):
            st.write("Tambah akun baru sekaligus (kosongkan kalau pakai akun yang sudah ada)")
            new_account = st.checkbox("Buat akun baru")
            existing_account = None if new_account else st.selectbox("Pilih akun", account_options)
            sales_owner = st.text_input("Sales owner (kalau buat akun baru)")
            referral_source = st.text_input("Sumber referral (kalau buat akun baru)")

            full_name = st.text_input("Nama lengkap")
            birthdate = st.date_input("Tanggal lahir", value=None, min_value=date(1950, 1, 1))
            relation_role = st.selectbox("Peran", ["bride", "groom", "parent", "sibling", "witness", "other"])
            phone = st.text_input("No. HP")
            email = st.text_input("Email")

            submitted = st.form_submit_button("Simpan profile")
            if submitted:
                if not full_name:
                    st.error("Nama lengkap wajib diisi.")
                else:
                    account_id = existing_account
                    if new_account:
                        account_id = next_id("account", "account_id", "ACC")
                        run_insert(
                            "INSERT INTO account (account_id, sales_owner, status, date_created, referral_source) VALUES (?,?,?,?,?)",
                            (account_id, sales_owner, "active", date.today().isoformat(), referral_source),
                        )
                    profile_id = next_id("profile", "profile_id", "PRF")
                    run_insert(
                        "INSERT INTO profile (profile_id, account_id, full_name, birthdate, relation_role, phone, email) VALUES (?,?,?,?,?,?,?)",
                        (profile_id, account_id, full_name, str(birthdate) if birthdate else None, relation_role, phone, email),
                    )
                    st.success(f"Profile {full_name} tersimpan ({profile_id}).")
                    st.rerun()

    # --- Relasi keluarga ---
    with input_tabs[1]:
        profiles = load("profile")
        prof_options = profiles["profile_id"] + " - " + profiles["full_name"] if not profiles.empty else []
        with st.form("form_family"):
            p_a = st.selectbox("Profile A", prof_options)
            p_b = st.selectbox("Profile B (terhubung ke)", prof_options)
            relation_type = st.selectbox("Jenis hubungan", ["sibling", "child", "parent", "cousin", "spouse", "other"])
            notes = st.text_input("Catatan")
            submitted = st.form_submit_button("Simpan relasi")
            if submitted:
                link_id = next_id("family_link", "link_id", "LNK")
                run_insert(
                    "INSERT INTO family_link (link_id, profile_id, related_profile_id, relation_type, notes) VALUES (?,?,?,?,?)",
                    (link_id, p_a.split(" - ")[0], p_b.split(" - ")[0], relation_type, notes),
                )
                st.success("Relasi keluarga tersimpan.")
                st.rerun()

    # --- Event baru ---
    with input_tabs[2]:
        profiles = load("profile")
        prof_options = profiles["profile_id"] + " - " + profiles["full_name"] if not profiles.empty else []
        with st.form("form_event"):
            p = st.selectbox("Profile", prof_options)
            event_date = st.date_input("Tanggal event", value=date.today())
            event_type = st.selectbox("Tipe event", ["wedding", "engagement", "anniversary_party", "other"])
            venue = st.text_input("Venue")
            status = st.selectbox("Status", ["inquiry", "confirmed", "completed", "cancelled"])
            submitted = st.form_submit_button("Simpan event")
            if submitted:
                event_id = next_id("event", "event_id", "EVT")
                run_insert(
                    "INSERT INTO event (event_id, profile_id, event_date, event_type, venue, status) VALUES (?,?,?,?,?,?)",
                    (event_id, p.split(" - ")[0], str(event_date), event_type, venue, status),
                )
                st.success(f"Event tersimpan ({event_id}).")
                st.rerun()

    # --- Revenue (admin only) ---
    with input_tabs[3]:
        if not is_admin:
            st.info("Hanya admin yang bisa input revenue.")
        else:
            events = load("event")
            event_options = events["event_id"] + " - " + events["event_type"] if not events.empty else []
            with st.form("form_revenue"):
                ev = st.selectbox("Event", event_options)
                amount = st.number_input("Jumlah (Rp)", min_value=0, step=1000000)
                payment_status = st.selectbox("Status pembayaran", ["unpaid", "partial", "paid"])
                due_date = st.date_input("Jatuh tempo", value=date.today())
                submitted = st.form_submit_button("Simpan revenue")
                if submitted:
                    revenue_id = next_id("revenue", "revenue_id", "REV")
                    run_insert(
                        "INSERT INTO revenue (revenue_id, event_id, amount, payment_status, due_date) VALUES (?,?,?,?,?)",
                        (revenue_id, ev.split(" - ")[0], amount, payment_status, str(due_date)),
                    )
                    st.success(f"Revenue tersimpan ({revenue_id}).")
                    st.rerun()

    # --- Notifikasi custom ---
    with input_tabs[4]:
        profiles = load("profile")
        prof_options = profiles["profile_id"] + " - " + profiles["full_name"] if not profiles.empty else []
        with st.form("form_notif"):
            p = st.selectbox("Profile", prof_options)
            notif_type = st.selectbox("Tipe notifikasi", ["custom_followup", "child_milestone", "other"])
            trigger_date = st.date_input("Tanggal reminder", value=date.today())
            submitted = st.form_submit_button("Simpan notifikasi")
            if submitted:
                notif_id = next_id("notification", "notif_id", "NOT")
                run_insert(
                    "INSERT INTO notification (notif_id, profile_id, event_id, notif_type, trigger_date, status) VALUES (?,?,?,?,?,?)",
                    (notif_id, p.split(" - ")[0], None, notif_type, str(trigger_date), "pending"),
                )
                st.success("Notifikasi custom tersimpan.")
                st.rerun()
