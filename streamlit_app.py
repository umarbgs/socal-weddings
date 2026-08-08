import streamlit as st
import pandas as pd
import sqlite3

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Wedding CRM",
    page_icon="💍",
    layout="wide"
)

DB_FILE = "wedding_crm.db"


# =========================
# LOAD DATA
# =========================
def load_table(table_name):
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query(
            f"SELECT * FROM '{table_name}'",
            conn
        )
        conn.close()
        return df

    except Exception as e:
        st.error(f"Error membaca tabel {table_name}")
        st.error(str(e))
        return pd.DataFrame()


# =========================
# LOGIN (OPTIONAL)
# =========================
try:

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:

        st.title("🔐 Login")

        username = st.text_input("Username")
        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button("Login"):

            if (
                username == st.secrets["USERNAME"]
                and password == st.secrets["PASSWORD"]
            ):
                st.session_state.logged_in = True
                st.rerun()

            else:
                st.error("Username atau Password salah")

        st.stop()

except:
    pass


# =========================
# LOAD TABLES
# =========================
profile_df = load_table("profile")
event_df = load_table("event")
revenue_df = load_table("revenue")
notification_df = load_table("notification")

# =========================
# SIDEBAR
# =========================
st.sidebar.title("💍 Wedding CRM")

page = st.sidebar.selectbox(
    "Menu",
    [
        "Dashboard",
        "Clients",
        "Events",
        "Revenue",
        "Notifications"
    ]
)

# =========================
# DASHBOARD
# =========================
if page == "Dashboard":

    st.title("💍 Wedding CRM Dashboard")

    total_client = len(profile_df)
    total_event = len(event_df)
    total_notification = len(notification_df)

    total_revenue = 0

    if not revenue_df.empty:

        numeric_cols = revenue_df.select_dtypes(
            include=["number"]
        ).columns

        if len(numeric_cols) > 0:
            total_revenue = revenue_df[
                numeric_cols[0]
            ].sum()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Clients",
        total_client
    )

    col2.metric(
        "Events",
        total_event
    )

    col3.metric(
        "Notifications",
        total_notification
    )

    col4.metric(
        "Revenue",
        f"{total_revenue:,.0f}"
    )

# =========================
# CLIENTS
# =========================
elif page == "Clients":

    st.title("👰 Client List")

    if profile_df.empty:

        st.warning("Data profile kosong")

    else:

        keyword = st.text_input(
            "Cari Client"
        )

        result = profile_df.copy()

        if keyword:

            result = result[
                result.astype(str)
                .apply(
                    lambda col:
                    col.str.contains(
                        keyword,
                        case=False,
                        na=False
                    )
                )
                .any(axis=1)
            ]

        st.dataframe(result)

# =========================
# EVENTS
# =========================
elif page == "Events":

    st.title("📅 Events")

    if event_df.empty:

        st.warning("Data event kosong")

    else:

        st.dataframe(event_df)

# =========================
# REVENUE
# =========================
elif page == "Revenue":

    st.title("💰 Revenue")

    if revenue_df.empty:

        st.warning("Data revenue kosong")

    else:

        st.dataframe(revenue_df)

# =========================
# NOTIFICATIONS
# =========================
elif page == "Notifications":

    st.title("🔔 Notifications")

    if notification_df.empty:

        st.warning("Data notification kosong")

    else:

        st.dataframe(notification_df)
