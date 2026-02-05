"""Streamlit frontend for the Yamuna Monitor prototype.
Run: streamlit run frontend/app.py
"""
import os
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

st.set_page_config(page_title="Yamuna Monitor", layout="wide")

st.sidebar.title("Yamuna Monitor")
page = st.sidebar.selectbox("Page", ["Dashboard", "Alerts", "Simulation", "Issues"])

# Optional Supabase auth (if configured). Falls back to demo login.
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client

        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None

if "user" not in st.session_state:
    st.session_state["user"] = None

st.sidebar.markdown("### Authentication")
if supabase:
    st.sidebar.write("Supabase auth available")
    if not st.session_state["user"]:
        email = st.sidebar.text_input("Email", key="email")
        pw = st.sidebar.text_input("Password", type="password", key="pw")
        if st.sidebar.button("Sign in"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pw})
                # res may contain 'session' and 'user'
                session = res.get("session") if isinstance(res, dict) else None
                user = res.get("user") if isinstance(res, dict) else None
                if session and user:
                    st.session_state["user"] = user
                    st.session_state["access_token"] = session.get("access_token")
                    st.sidebar.success("Signed in")
                else:
                    st.sidebar.error("Sign in failed")
            except Exception:
                st.sidebar.error("Auth error")
        if st.sidebar.button("Sign up"):
            try:
                supabase.auth.sign_up({"email": email, "password": pw})
                st.sidebar.info("Signup requested. Check email for confirmation.")
            except Exception:
                st.sidebar.error("Signup failed")
    else:
        st.sidebar.write(f"Signed in: {st.session_state['user'].get('email')}")
        if st.sidebar.button("Sign out"):
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
            st.session_state["user"] = None
else:
    st.sidebar.info("Supabase not configured — demo login available")
    if not st.session_state["user"]:
        demo_user = st.sidebar.text_input("Demo username", key="demo_user")
        if st.sidebar.button("Demo login"):
            st.session_state["user"] = {"email": demo_user or "demo"}
            st.sidebar.success("Signed in (demo)")
    else:
        st.sidebar.write(f"Signed in: {st.session_state['user'].get('email')}")
        if st.sidebar.button("Sign out demo"):
            st.session_state["user"] = None


def fetch_sensors():
    try:
        resp = requests.get(f"{API_BASE}/sensors")
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        return []
    return []


def dashboard():
    st.title("Dashboard")
    sensors = fetch_sensors()

    cols = st.columns([1, 2])
    with cols[0]:
        st.subheader("Sensors Map")
        if sensors:
            dfmap = pd.DataFrame(sensors)
            st.map(dfmap[["lat", "lon"]])
        else:
            st.info("No sensors detected. Run the server and seed sensors with scripts/init_db.py and start data generator.")

    with cols[1]:
        st.subheader("Live Readings (latest)")
        if sensors:
            sid = st.selectbox("Choose sensor", [s["id"] for s in sensors])
            resp = requests.get(f"{API_BASE}/readings/{sid}?limit=200")
            if resp.status_code == 200:
                rows = resp.json()
                df = pd.DataFrame(rows)
                if not df.empty:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    st.write("Latest:")
                    st.dataframe(df.sort_values("timestamp").tail(5))
                    fig = px.line(df.sort_values("timestamp"), x="timestamp", y=["pH", "BOD", "COD", "turbidity"], title=f"Sensor {sid} readings")
                    st.plotly_chart(fig, use_container_width=True)

                    if st.button("Predict risk for next 24h"):
                        resp2 = requests.post(f"{API_BASE}/predict-risk", json={"sensor_id": sid})
                        if resp2.status_code == 200:
                            res = resp2.json()
                            next_24 = res.get("next_24h", [])
                            if next_24:
                                dfp = pd.DataFrame(next_24)
                                dfp["ts"] = pd.to_datetime(dfp["ts"])
                                fig2 = px.line(dfp, x="ts", y="risk", title=f"Predicted risk (next 24h) - Sensor {sid}")
                                st.plotly_chart(fig2, use_container_width=True)
                        else:
                            st.error("Failed to fetch prediction")
                else:
                    st.info("No readings yet for selected sensor.")
            else:
                st.error("Failed to fetch readings")
        else:
            st.info("No sensors available")


def alerts_page():
    st.title("Alerts")
    unresolved = st.checkbox("Show unresolved only", value=True)
    resp = requests.get(f"{API_BASE}/alerts?unresolved_only={str(unresolved).lower()}")
    if resp.status_code == 200:
        rows = resp.json()
        if rows:
            for a in rows:
                with st.expander(f"Alert {a['id']} - {a['severity']}"):
                    st.write(a)
                    if not a.get("resolved"):
                        if st.button("Resolve", key=f"resolve-{a['id']}"):
                            # require supabase auth token to resolve
                            token = st.session_state.get("access_token")
                            if not token:
                                st.error("Sign in with Supabase to resolve alerts")
                            else:
                                headers = {"Authorization": f"Bearer {token}"}
                                r = requests.post(f"{API_BASE}/alerts/{a['id']}/resolve", headers=headers)
                                if r.status_code == 200:
                                    st.success("Resolved")
                                    st.experimental_rerun()
                                else:
                                    st.error("Failed to resolve")
        else:
            st.info("No alerts")
    else:
        st.error("Could not fetch alerts")


def simulation_page():
    st.title("Policy Simulation")
    sid = st.number_input("Sensor ID", min_value=1, max_value=1000, value=1)
    pct = st.slider("Reduce pollutant discharges by %", min_value=0, max_value=100, value=20)
    if st.button("Simulate"):
        resp = requests.post(f"{API_BASE}/simulate-policy", json={"sensor_id": sid, "reduction_pct": pct})
        if resp.status_code == 200:
            res = resp.json()
            # prefer projected_baseline if supplied by backend, else use baseline
            st.metric("Baseline risk", round(res.get("projected_baseline", res.get("baseline", 0)), 2))
            next_24 = res.get("next_24h", [])
            if next_24:
                df = pd.DataFrame(next_24)
                df["ts"] = pd.to_datetime(df["ts"])
                fig = px.line(df, x="ts", y="risk", title=f"Projected risk (next 24h) after {pct}% reduction")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Simulation failed")


def issues_page():
    st.title("Issues")
    with st.form("create_issue"):
        t = st.text_input("Title")
        d = st.text_area("Description")
        user = st.text_input("Reported by")
        submitted = st.form_submit_button("Create")
        if submitted:
            resp = requests.post(f"{API_BASE}/issues", json={"title": t, "description": d, "created_by": user})
            if resp.status_code == 200:
                st.success("Issue created")
            else:
                st.error("Failed to create issue")

    if st.button("Refresh issues"):
        resp = requests.get(f"{API_BASE}/issues")
        if resp.status_code == 200:
            rows = resp.json()
            if rows:
                df = pd.DataFrame(rows)
                st.dataframe(df)
                # allow closing an issue
                for i in rows:
                    if i.get("status") != "closed":
                        if st.button(f"Close issue {i['id']}", key=f"close-{i['id']}"):
                            token = st.session_state.get("access_token")
                            if not token:
                                st.error("Sign in with Supabase to close issues")
                            else:
                                headers = {"Authorization": f"Bearer {token}"}
                                r = requests.patch(f"{API_BASE}/issues/{i['id']}", json={"status": "closed"}, headers=headers)
                                if r.status_code == 200:
                                    st.success("Issue closed")
                                    st.experimental_rerun()
                                else:
                                    st.error("Failed to close")
            else:
                st.info("No issues yet")


if page == "Dashboard":
    dashboard()
elif page == "Alerts":
    alerts_page()
elif page == "Simulation":
    simulation_page()
elif page == "Issues":
    issues_page()
