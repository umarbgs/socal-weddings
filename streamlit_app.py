import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# ==================================================
# CONFIG
# ==================================================
st.set_page_config(
    page_title="Wedding CRM Dashboard",
    page_icon="💍",
    layout="wide"
)

DB_FILE = "wedding_crm.db"

# ==================================================
# DATABASE
# ==================================================
@st.cache_data
def load_table(table_name):
    conn = sqlite3.connect(DB_FILE)

    try:
        df = pd.read_sql(
            f"SELECT * FROM {table_name}",
            conn
        )
    except:
        df = pd.DataFrame()

    conn.close()
    return df


profile_df = load_table("profile")
event_df = load_table("event")
revenue_df = load_table("revenue")
notification_df = load_table("notification")

# ==================================================
# SIDEBAR
# ==================================================
st.sidebar.title("💍 Wedding CRM")

menu = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Clients",
        "Events",
        "Revenue",
        "Notifications"
    ]
)

# ==================================================
# DASHBOARD
# ==================================================
if menu == "Dashboard":

    st.title("💍 Wedding CRM Dashboard")

    total_clients = len(profile_df)

    total_events = len(event_df)

    total_notifications = len(notification_df)

    total_revenue = 0

    if not revenue_df.empty:

        revenue_cols = revenue_df.select_dtypes(
            include="number"
        ).columns

        if len(revenue_cols) > 0:
            total_revenue = revenue_df[revenue_cols[0]].sum()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Clients", total_clients)
    c2.metric("Events", total_events)
    c3.metric("Notifications", total_notifications)
    c4.metric("Revenue", f"${total_revenue:,.0f}")

    st.divider()

    if not event_df.empty:

        st.subheader("Upcoming Events")

        st.dataframe(
            event_df.head(10),
            use_container_width=True
        )

    if not revenue_df.empty:

        st.subheader("Revenue Chart")

        numeric_cols = revenue_df.select_dtypes(
            include="number"
        ).columns

        if len(numeric_cols) > 0:

            fig = px.histogram(
                revenue_df,
                x=numeric_cols[0],
                title="Revenue Distribution"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

# ==================================================
# CLIENTS
# ==================================================
elif menu == "Clients":

    st.title("👰 Client Profiles")

    if profile_df.empty:
        st.warning("No data found")
    else:

        search = st.text_input(
            "Search Client"
        )

        filtered = profile_df.copy()

        if search:

            filtered = filtered[
                filtered.astype(str)
                .apply(
                    lambda x: x.str.contains(
                        search,
                        case=False,
                        na=False
                    )
                )
                .any(axis=1)
            ]

        st.dataframe(
            filtered,
            use_container_width=True
        )

# ==================================================
# EVENTS
# ==================================================
elif menu == "Events":

    st.title("📅 Events")

    if event_df.empty:
        st.warning("No event data found")
    else:

        st.dataframe(
            event_df,
            use_container_width=True
        )

# ==================================================
# REVENUE
# ==================================================
elif menu == "Revenue":

    st.title("💰 Revenue")

    if revenue_df.empty:
        st.warning("No revenue data found")

    else:

        st.dataframe(
            revenue_df,
            use_container_width=True
        )

        numeric_cols = revenue_df.select_dtypes(
            include="number"
        ).columns

        if len(numeric_cols) > 0:

            fig = px.bar(
                revenue_df,
                y=numeric_cols[0],
                title="Revenue"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

# ==================================================
# NOTIFICATION
# ==================================================
elif menu == "Notifications":

    st.title("🔔 Notifications")

    if notification_df.empty:
        st.warning("No notification data found")
    else:

        st.dataframe(
            notification_df,
            use_container_width=True
        )
